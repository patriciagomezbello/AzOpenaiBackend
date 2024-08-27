import os

from azure.storage.blob import BlobProperties
from cli.core.utils import is_url_encoded
from cli.models import CategoryRBACMap
from cli.models import CLIConfig
from dataloader.base import new_logger
from dataloader.indexer import Indexer
from dataloader.indexer.models import AccessModel
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders import BlobInteractor
from dataloader.loaders.models import File

blob_interactor: BlobInteractor = None  # type: ignore # Will be set by the service
indexer: Indexer = None  # type: ignore # Will be set by the service


logger = new_logger(__name__)


def set_blob_interactor(interactor: BlobInteractor) -> None:
    global blob_interactor
    blob_interactor = interactor


def set_indexer(index: Indexer) -> None:
    global indexer
    indexer = index


async def load_and_index_files(config: CLIConfig) -> None:
    logger.info("Starting to load and index files", extra={"file_mode": config.file_mode})

    index_files: list[File] = []
    remove_files: list[DocumentInfo] = []
    match config.file_mode:
        case "blob":
            index_files, remove_files = await handle_blob_mode(config)
        case "git":
            index_files, remove_files = await handle_git_mode(config)
        case _:
            logger.error("Mode not supported", extra={"file_mode": config.file_mode})
            raise ValueError(f"Mode '{config.file_mode}' not supported.")

    failed = await indexer.index_documents(documents=index_files, reset=config.reset_index)
    if len(failed) > 0:
        logger.error("Failed to index documents", extra={"failed_count": len(failed)})
        raise ValueError(f"Failed to index {len(failed)} documents.")

    for doc in remove_files:
        await indexer.delete_document(doc)

    logger.info(
        "Successfully loaded, indexed updated files, and removed deleted files",
        extra={"count_indexed": len(index_files), "count_removed": len(remove_files)},
    )


async def handle_blob_mode(config: CLIConfig) -> tuple[list[File], list[DocumentInfo]]:
    logger.info(
        "Synchronizing files between containers",
        extra={"data_container": config.data_container, "docs_container": config.docs_container},
    )
    updated_files: list[File] = []
    removed_files: list[DocumentInfo] = []
    data_blobs = [blob async for blob in blob_interactor.list_blobs(container=config.data_container)]
    docs_blobs = [blob async for blob in blob_interactor.list_blobs(container=config.docs_container)]

    add, remove = await sync_docs_container(data_blobs, docs_blobs, config.role_config)
    updated_files.extend(add)
    removed_files.extend(remove)

    updated_files.extend(
        await sync_data_container(config.data_container, config.docs_container, data_blobs, docs_blobs, config.reset_index),
    )
    return updated_files, removed_files


async def handle_git_mode(config: CLIConfig) -> tuple[list[File], list[DocumentInfo]]:
    files: list[File] = []
    to_remove: list[DocumentInfo] = []
    local_files = get_local_files(config.local_files, config.role_config)
    # TODO: should we delete files that are not in the local directory?
    # I think if someone uses both git and blob mode, they might want to keep the files in the blob container
    async for file, uploaded in blob_interactor.upload_files(local_files):
        if uploaded or config.reset_index:
            files.append(file)
    return files, to_remove


def get_category(blob_name: str) -> str:
    category = File.build_directory_name(blob_name) or ""
    logger.debug("Determined category for blob", extra={"blob_name": blob_name, "category": category})
    return category


async def download_and_set_metadata(blob_name: str, category: str, role_config: CategoryRBACMap) -> File:
    logger.info("Downloading file and setting metadata for blob", extra={"blob_name": blob_name})
    file = await blob_interactor.download_file(blob_name)
    file.metadata.category = category
    file.metadata.roles = role_config.get_roles(category)
    return file


def needs_metadata_update(blob: BlobProperties, category: str, role_config: CategoryRBACMap) -> bool:
    rbac = AccessModel(category=category, roles=role_config.get_roles(category)).model_dump_json()
    needs_update = "rbac" not in blob.metadata or blob.metadata["rbac"] != rbac
    logger.debug("Checked if metadata update is needed", extra={"blob_name": blob.name, "needs_update": needs_update})
    return needs_update


async def update_blob_metadata(blob_name: str, category: str, role_config: CategoryRBACMap, metadata: dict[str, str]) -> File:
    logger.info("Updating metadata for blob", extra={"blob_name": blob_name})
    blob_client = blob_interactor.container_client.get_blob_client(blob_name)
    metadata["rbac"] = AccessModel(category=category, roles=role_config.get_roles(category)).model_dump_json()
    await blob_client.set_blob_metadata(metadata)
    return await blob_interactor.download_file(blob_name)


async def sync_docs_container(
    data_blobs: list[BlobProperties],
    docs_blobs: list[BlobProperties],
    rbac: CategoryRBACMap,
) -> tuple[list[File], list[DocumentInfo]]:
    """Sync files from the docs container to the data container by updating metadata or deleting files."""
    files: list[File] = []
    to_remove: list[DocumentInfo] = []
    data_blob_names = [blob.name for blob in data_blobs]
    for blob in docs_blobs:
        if blob.name in data_blob_names:
            # Metadata can be None even though the type hint says otherwise, this is a bug in the Azure SDK
            # TODO: check for an open issue in the Azure SDK and link it here
            if not blob.metadata or len(blob.metadata) == 0:
                logger.info("Found manually uploaded file in docs container. Adding to files list", extra={"filename": blob.name})
                files.append(await download_and_set_metadata(blob.name, get_category(blob.name), rbac))
                continue

            if needs_metadata_update(blob, get_category(blob.name), rbac):
                logger.info("Metadata needs to be updated for file in docs container", extra={"filename": blob.name})
                files.append(await update_blob_metadata(blob.name, get_category(blob.name), rbac, blob.metadata))
                continue

            logger.info("File found in data container while syncing docs container. Skipping", extra={"filename": blob.name})
            continue

        if is_url_encoded(blob.name):
            logger.info("Web document found in docs container. Skipping", extra={"filename": blob.name})
            continue

        logger.info("File not found in data container. Deleting from docs container", extra={"filename": blob.name})
        _ = await blob_interactor.delete_file(blob.name)
        access = AccessModel.model_validate(blob.metadata.get("rbac", "{}"))
        to_remove.append(DocumentInfo(name=blob.name, category=access.category, roles=access.roles))
    return files, to_remove


async def sync_data_container(
    data_container: str,
    docs_container: str,
    data_blobs: list[BlobProperties],
    docs_blobs: list[BlobProperties],
    reset_index: bool,
) -> list[File]:
    """Sync files from the data container to the docs container by uploading new files."""
    files: list[File] = []
    docs_blob_names = [blob.name for blob in docs_blobs]
    for blob in data_blobs:
        if blob.name in docs_blob_names:
            file = await blob_interactor.download_file(blob.name, container=docs_container)
            if await blob_interactor.is_file_identical(file, container=data_container, skip_metadata=True):
                logger.info("File is identical to file in data container. Skipping", extra={"filename": blob.name})
                if reset_index:
                    files.append(file)
                continue

            logger.info(
                "File found in docs container but the file in the data container has changed. Forcing upload",
                extra={"filename": blob.name},
            )
            _ = await blob_interactor.force_upload_file(file, container=docs_container)
            files.append(file)
            continue

        logger.info("New file found in data container. Moving to docs container", extra={"filename": blob.name})
        file = await blob_interactor.download_file(blob.name, container=data_container)
        try:
            _ = await blob_interactor.force_upload_file(file, container=docs_container)
        except Exception as e:
            logger.exception("Failed to upload file to docs container", extra={"filename": blob.name, "exception": str(e)})
            continue
        files.append(file)
    return files


def get_local_files(path: str, role_config: CategoryRBACMap) -> list[File]:
    """Get files from a local path and set the metadata based on the file path."""
    logger.info("Getting local files from path", extra={"path": path})
    files: list[File] = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            segments = os.path.join(root, filename).split("/")
            category = segments[1] if segments[1] != filename else ""
            with open(os.path.join(root, filename), "rb") as f:
                content = f.read()
            file = File(
                metadata=DocumentInfo(
                    name=filename,
                    category=category,
                    roles=role_config.get_roles(category),
                ),
                content=content,
                path=os.path.join(*segments[1:]),
            )
            logger.debug(
                "Found local file", extra={"file_path": os.path.join(root, filename), "file_metadata": file.metadata.model_dump()}
            )
            files.append(file)
    logger.info("Found files in path", extra={"path": path, "file_count": len(files)})
    return files
