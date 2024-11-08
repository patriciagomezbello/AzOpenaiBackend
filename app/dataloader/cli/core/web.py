import json
from collections.abc import Sequence

from azure.storage.blob import BlobProperties
from cli.models import CLIConfig
from dataloader.base import is_url
from dataloader.base import new_logger
from dataloader.indexer import Indexer
from dataloader.indexer.models import AccessModel
from dataloader.indexer.models import DocumentInfo
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


async def load_web(config: LoaderConfig) -> tuple[list[WebDocument], list[WebDocument]]:
    loader_name = str(config.name).capitalize()
    logger.info(f"Loading and indexing web documents using '{loader_name}'")
    try:
        loader = WEBLOADER_REGISTRY[config.name](config)
    except KeyError:
        logger.error(f"Web Loader '{loader_name}' not supported.")
        raise ValueError(f"Web Loader {str(config.name)=} not supported.")

    documents: dict[str, WebDocument] = {}
    async for doc in loader.alazy_load():
        logger.debug(f"Loaded document from {loader_name}", extra={"name": doc.metadata.name})
        documents[doc.metadata.name] = doc

    logger.info(f"Loaded {len(documents)} documents from {config.config.get_url()}")
    files = [doc.to_file() for doc in documents.values()]

    to_index: list[WebDocument] = []

    async for file, uploaded in blob_interactor.upload_files(files, overwrite=True):
        if uploaded:
            if doc := documents.get(file.metadata.name):
                to_index.append(doc)

    logger.info(f"Uploaded {len(to_index)} web documents to blob storage.")

    return to_index, [doc for doc in documents.values()]


async def index_web(
    cli_config: CLIConfig,
    to_index: list[WebDocument],
    documents: list[WebDocument],
) -> tuple[Sequence[DocumentInfo], dict[str, int]]:

    summary: dict[str, int] = {}

    indexed_web_blobs: list[BlobProperties] = []

    async for blob in blob_interactor.list_blobs(ensure_exists=True):
        if is_url(blob.metadata.get("name", "")):
            indexed_web_blobs.append(blob)

    # documentinfo and blob_name
    web_docs_to_delete: list[tuple[DocumentInfo, str]] = []

    defined_web_documents = [item.metadata.name for item in documents]
    print(f"defined web docs: \n\n{defined_web_documents}")
    for blob in indexed_web_blobs:
        name = blob.metadata.get("name")
        rbac = blob.metadata.get("rbac")
        if rbac:
            rbac_model = AccessModel(**json.loads(rbac))
        if name and name not in defined_web_documents:
            web_docs_to_delete.append((DocumentInfo(name=name, category=rbac_model.category), blob.name))

    for metadata, blob_name in web_docs_to_delete:
        _ = await blob_interactor.delete_file(blob_name)
        await indexer.delete_document(metadata)
        logger.info(f"Deleted document: {metadata.name}")
    logger.info("Successfully deleted Langchain documents", extra={"count": len(web_docs_to_delete)})

    summary = await indexer.index_documents(
        documents=to_index,
        max_section_length=cli_config.max_section_length,
    )
    if len(failed := [doc for doc in to_index if doc.metadata.name not in summary.keys()]) > 0:
        logger.error(f"Failed to index {len(failed)} documents.")
        raise ValueError(f"Failed to index {len(failed)} documents.")

    logger.info(f"Loaded and indexed {len(to_index)} web documents.")
    return [doc.metadata for doc in to_index], summary
