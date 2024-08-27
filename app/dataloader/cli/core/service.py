from cli.models import CLIConfig
from dataloader.extractor import DocumentIntelligence
from dataloader.indexer import Indexer
from dataloader.loaders import BlobInteractor
from dataloader.loaders.models import File
from dataloader.loaders.models import WebDocument


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

    async def load_file_mode(self, _: bool) -> None:
        from cli.core.file import set_blob_interactor
        from cli.core.file import set_indexer
        from cli.core.file import load_and_index_files

        set_blob_interactor(self.blob_interactor)
        set_indexer(self.indexer)

        await load_and_index_files(self.config)

    async def load_lc_mode(self, reset_status: bool) -> None:
        from cli.core.web import set_blob_interactor
        from cli.core.web import set_indexer
        from cli.core.web import load_and_index_web

        set_blob_interactor(self.blob_interactor)
        set_indexer(self.indexer)

        for cfg in self.config.loader_config:
            await load_and_index_web(cfg, self.config, reset_status)

    async def close(self) -> None:
        await self.blob_interactor.close_clients()
        await self.indexer.close_clients()
