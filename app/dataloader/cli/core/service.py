from collections.abc import Sequence

from cli.models import CLIConfig
from dataloader.base import new_logger
from dataloader.extractor import DocumentIntelligence
from dataloader.indexer import Indexer
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders import BlobInteractor
from dataloader.loaders.models import File
from dataloader.loaders.models import WebDocument


logger = new_logger(__name__)


class Service:
    def __init__(self, blob_interactor: BlobInteractor, indexer: Indexer, config: CLIConfig):
        self.blob_interactor = blob_interactor
        self.indexer = indexer
        if config.indexer_config.extractor is None:
            raise ValueError("Extractor configuration is missing.")

        self.ocr = DocumentIntelligence(config.indexer_config.extractor, indexer.credential)
        self.indexer.set_extractor(File, self.ocr.extract_pages)
        self.indexer.set_extractor(WebDocument, WebDocument.to_pages)
        self.config = config

    async def load_file_mode(self) -> tuple[Sequence[DocumentInfo], dict[str, int]]:
        from cli.core.file import set_blob_interactor
        from cli.core.file import set_indexer
        from cli.core.file import load_and_index_files

        set_blob_interactor(self.blob_interactor)
        set_indexer(self.indexer)

        return await load_and_index_files(self.config)

    async def load_lc_mode(self) -> tuple[Sequence[DocumentInfo], dict[str, int]]:
        from cli.core.web import set_blob_interactor
        from cli.core.web import set_indexer
        from cli.core.web import load_web
        from cli.core.web import index_web

        set_blob_interactor(self.blob_interactor)
        set_indexer(self.indexer)

        indexed_documents: Sequence[DocumentInfo] = []
        summary: dict[str, int] = {}

        to_index: list[WebDocument] = []
        documents: list[WebDocument] = []

        for cfg in self.config.loader_config:
            logger.info(f"Loading web documents using '{cfg.name}'")
            t, d = await load_web(cfg)
            to_index.extend(t)
            documents.extend(d)

        logger.info("Indexing all web documents")
        indexed, sum = await index_web(cli_config=self.config, to_index=to_index, documents=documents)

        indexed_documents.extend(indexed)
        summary.update(sum)

        return indexed_documents, summary

    async def purge_chunk_corpses(self, summary: dict[str, int]) -> None:
        # TODO: fix this for web documents
        async def purge_chunk(sourcefile: str, chunks: int) -> None:
            try:
                filter = f"sourcefile eq '{sourcefile}'"
                documents = await self.indexer.searcher.search(
                    search_text="*",
                    filter=filter,
                    select=["id", "sourcefile", "sourcepage"],
                )
                sorted_chunks = sorted([doc async for doc in documents], key=lambda doc: str(doc["id"]).rsplit("-", 1)[-1])
                if len(sorted_chunks) > chunks:
                    _ = await self.indexer.searcher.delete_documents(sorted_chunks[chunks:])
                    logger.info(f"Purged {len(sorted_chunks) - chunks} chunks from the index for '{sourcefile}'.")
                    logger.debug(f"Chunks purged: {sorted_chunks[chunks:]}", extra={"sorted": len(sorted_chunks), "chunks": chunks})
                    return
                logger.info(f"No chunks to purge for '{sourcefile}'.")
            except Exception as e:
                logger.error(f"Failed to purge chunks for '{sourcefile}': {e}")

        for sourcefile, chunks in summary.items():
            logger.info(f"Purging chunks for '{sourcefile}' with {chunks} chunks.")
            await purge_chunk(sourcefile, chunks)

    async def purge_doc_corpses(self, indexed: Sequence[DocumentInfo]) -> None:
        unique = {metadata.get_name() for metadata in indexed}
        filter = " and ".join([f"sourcefile ne '{name}'" for name in unique])
        documents = await self.indexer.searcher.search(
            search_text="*",
            filter=filter,
            select=["id", "sourcefile"],
        )
        to_delete = [doc async for doc in documents]
        if len(to_delete) > 0:
            _ = await self.indexer.searcher.delete_documents(to_delete)
            _ = [await self.blob_interactor.delete_file(doc["sourcefile"]) for doc in to_delete]
        logger.info(f"Purged {len(to_delete)} documents from the index.", extra={"unique": len(unique), "filter": filter})
        logger.debug(f"Documents purged: {to_delete}")

    async def close(self) -> None:
        await self.blob_interactor.close_clients()
        await self.indexer.close_clients()
