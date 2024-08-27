from cli.models import CLIConfig
from dataloader.base import new_logger
from dataloader.indexer import Indexer
from dataloader.loaders import BlobInteractor
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import WebDocument
from dataloader.loaders.models import WEBLOADER_REGISTRY

blob_interactor: BlobInteractor = None  # type: ignore # Will be set by the service
indexer: Indexer = None  # type: ignore # Will be set by the service


logger = new_logger(__name__)


def set_blob_interactor(interactor: BlobInteractor) -> None:
    global blob_interactor
    blob_interactor = interactor


def set_indexer(index: Indexer) -> None:
    global indexer
    indexer = index


async def load_and_index_web(config: LoaderConfig, cli_config: CLIConfig, reset_status: bool) -> None:
    logger.info("Starting to load and index Langchain documents", extra={"lc_mode": cli_config.lc_mode})
    try:
        loader = WEBLOADER_REGISTRY[config.name](config)
    except KeyError:
        logger.error(f"Loader {config.name=} not supported.")
        raise ValueError(f"Loader {config.name=} not supported.")

    documents = loader.load()
    logger.info("Loaded documents from Langchain", extra={"count": len(documents)})

    files = [doc.to_file() for doc in documents]
    docs = {doc.metadata.name: doc for doc in documents}

    match cli_config.lc_mode:
        case "create":
            to_index: list[WebDocument] = []
            async for file, uploaded in blob_interactor.upload_files(files):
                if uploaded or cli_config.reset_index or reset_status:
                    if doc := docs.get(file.metadata.name):
                        to_index.append(doc)
            logger.info("Uploaded web documents to blob storage", extra={"count": len(to_index)})

            failed = await indexer.index_documents(documents=to_index, reset=cli_config.reset_index)
            if len(failed) > 0:
                logger.error("Failed to index documents", extra={"failed_count": len(failed)})
                raise ValueError(f"Failed to index {len(failed)} documents.")
            logger.info("Successfully loaded and indexed Langchain documents", extra={"count": len(to_index)})
        case "delete":
            for file in files:
                await blob_interactor.delete_file(file.get_blob_name())
                logger.info(f"Deleted file: {file.get_blob_name()}")
            for doc in documents:
                await indexer.delete_document(doc.metadata)
                logger.info(f"Deleted document: {doc.metadata.name}")
            logger.info("Successfully deleted Langchain documents", extra={"count": len(files)})
        case _:
            logger.error(f"Mode {cli_config.lc_mode} not supported.")
            raise ValueError(f"Mode {cli_config.lc_mode} not supported.")
