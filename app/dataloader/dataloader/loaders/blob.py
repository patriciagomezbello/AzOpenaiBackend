import hashlib
import json
import mimetypes
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from azure.identity.aio import ChainedTokenCredential
from azure.storage.blob import BlobProperties
from azure.storage.blob import StorageStreamDownloader
from azure.storage.blob.aio import BlobServiceClient
from dataloader.base import ClientManager
from dataloader.base import new_logger
from dataloader.indexer.models import AccessModel
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders.models import File


logger = new_logger(__name__)


class BlobInteractor(ClientManager):
    def __init__(self, account: str, container: str, credential: ChainedTokenCredential):
        super().__init__(credential)
        self.client = BlobServiceClient(account_url=f"https://{account}.blob.core.windows.net", credential=credential)
        self.container_client = self.client.get_container_client(container)

    async def list_blobs(
        self,
        *,
        include: str | list[str] | None = "metadata",
        name_starts_with: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[BlobProperties, None]:
        """List blobs in the container. Yields the BlobProperties.
        To use another container as the default, pass the container name as a keyword argument.
        You can also pass the keyword argument 'ensure_exists' to ensure the container exists before listing blobs.

        You can pass additional keyword arguments to the list_blobs method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.containerclient?view=azure-python#azure-storage-blob-containerclient-list-blobs).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None), ensure_exists=kwargs.pop("ensure_exists", False)):
            async for blob in self.container_client.list_blobs(include=include, name_starts_with=name_starts_with, **kwargs):
                yield blob

    async def download_file(
        self,
        blob: str,
        *,
        offset: int | None = None,
        length: int | None = None,
        **kwargs: Any,
    ) -> File:
        """Download a file from the blob. Raises a FileNotFoundError if the file does not exist.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the download_blob method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-download-blob).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None), ensure_exists=False):
            try:
                downloader: StorageStreamDownloader[bytes] | StorageStreamDownloader[str] = (
                    await self.container_client.download_blob(blob, offset=offset, length=length, **kwargs)
                )
            except Exception as e:
                raise FileNotFoundError(f"File {blob} not found") from e

            mimetype = downloader.properties.content_settings.content_type or "application/octet-stream"
            if mimetype == "application/octet-stream":
                mimetype = mimetypes.guess_type(blob)[0] or "application/octet-stream"
            metadata = downloader.properties.metadata
            rbcac: dict[str, Any] = json.loads(metadata.get("rbac", "{}"))

            access = AccessModel(category=rbcac.get("category", ""), roles=rbcac.get("roles", ["public"]))
            return File(
                path=File.build_blob_name(os.path.basename(blob), blob),
                metadata=DocumentInfo(
                    name=metadata.get("name", File.build_file_name(os.path.basename(blob), blob)),
                    category=access.category,
                    roles=access.roles,
                    language=metadata.get("language"),
                ),
                content=await downloader.readall(),  # type: ignore # Azure Storage SDK typing issue
                mimetype=mimetype,
            )

    async def upload_file(self, file: File, /, **kwargs: Any) -> bool:
        """Upload a file to the blob. Returns True if the file was uploaded, False if it was identical.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the upload_blob method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-upload-blob).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None)):
            try:
                if await self.is_file_identical(file):
                    return False
                _ = await self._upload_to_blob(file, **kwargs)
                return True
            except Exception as e:
                raise ValueError(f"Failed to upload {file.metadata.name}") from e

    async def upload_files(self, files: list[File], /, **kwargs: Any) -> AsyncGenerator[tuple[File, bool], None]:
        """Upload a list of files to the blob. Yields the file and a boolean indicating if the file was uploaded.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the upload_blob method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-upload-blob).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None)):
            file_hashes = {file.get_blob_name(): hashlib.md5(file.get_content(bytes)).digest() for file in files}
            blob_hashes: dict[str, bytes] = {}
            async for blob in self.list_blobs(include=None):
                if blob.content_settings.content_md5:
                    blob_hashes[blob.name] = bytes(blob.content_settings.content_md5)
                    continue

                try:
                    blob_client = self.container_client.get_blob_client(blob.name)
                    content = await (await blob_client.download_blob()).readall()
                    blob_hashes[blob.name] = hashlib.md5(content).digest()
                except Exception as e:
                    logger.error(f"Failed to download blob '{blob.name}': {e}")
                    blob_hashes[blob.name] = b""

            for file in files:
                file_name = file.get_blob_name()
                if file_name in blob_hashes and blob_hashes[file_name] == file_hashes[file_name]:
                    yield file, False
                    continue
                await self._upload_to_blob(file, **kwargs)
                yield file, True

    async def force_upload_file(self, file: File, /, **kwargs: Any) -> dict[str, Any]:
        """Upload a file to the blob, without checking if the content is identical. Returns the updated blob properties.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the upload_blob method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-upload-blob).
        """  # noqa: E501
        if "overwrite" not in kwargs:
            kwargs["overwrite"] = True
        async with self._container_manager(kwargs.pop("container", None)):
            try:
                return await self._upload_to_blob(file, **kwargs)
            except Exception as e:
                raise ValueError(f"Failed to upload {file.metadata.name}") from e

    async def delete_file(self, blob: str, /, **kwargs: Any) -> bool:
        """Delete a file from the blob. Returns True if the file was deleted, False if it did not exist.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the delete_blob method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-delete-blob).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None), ensure_exists=False):
            if not await self.container_client.exists():
                return False

            blob_client = self.container_client.get_blob_client(blob)
            await blob_client.delete_blob(**kwargs)
            return True

    async def is_file_identical(
        self,
        new: File,
        *,
        skip_metadata: bool = False,
        skip_content: bool = False,
        **kwargs: Any,
    ) -> bool:
        """Check if the file is identical to the existing file in the blob.
        To use another container as the default, pass the container name as a keyword argument.

        You can pass additional keyword arguments to the get_blob_properties method.
        For more information, see the [Azure Blob Storage SDK docs](https://learn.microsoft.com/en-us/python/api/azure-storage-blob/azure.storage.blob.blobclient?view=azure-python#azure-storage-blob-blobclient-get-blob-properties).
        """  # noqa: E501
        async with self._container_manager(kwargs.pop("container", None), ensure_exists=False):
            blob_name = new.get_blob_name()
            blob_client = self.container_client.get_blob_client(blob_name)

            try:
                props = await blob_client.get_blob_properties()
                if props.content_settings.content_md5 and not skip_content:
                    if bytes(props.content_settings.content_md5) == hashlib.md5(new.get_content(bytes)).digest():
                        return True
            except FileNotFoundError:
                return False

            try:
                existing = await self.download_file(blob_name)
            except FileNotFoundError:
                return False

            existing_content = existing.get_content(bytes)
            new_content = new.get_content(bytes)
            metadata = existing.metadata == new.metadata or skip_metadata
            content = hashlib.sha256(existing_content).hexdigest() == hashlib.sha256(new_content).hexdigest() or skip_content
            return metadata and content

    @asynccontextmanager
    async def _container_manager(self, container: str | None = None, *, ensure_exists: bool = True) -> AsyncGenerator[None, None]:
        """A container manager to switch the default container for the interactor and optionally ensure it exists."""
        container_client = self.container_client
        if container and container != self.container_client.container_name:
            self.container_client = self.client.get_container_client(container)

        try:
            if ensure_exists:
                await self._ensure_container()
            yield
        finally:
            self.container_client = container_client

    async def _ensure_container(self) -> None:
        """Ensure the container exists."""
        if not await self.container_client.exists():
            _ = await self.container_client.create_container()

    async def _upload_to_blob(self, file: File, **kwargs: Any) -> dict[str, Any]:
        """Upload the file to the blob. Returns the updated blob properties.
        It will neither check if the file is identical nor ensure the container exists.
        """
        blob_client = self.container_client.get_blob_client(file.get_blob_name())
        metadata = self._merge_metadata(file, kwargs.pop("metadata", None))
        logger.info(f"Uploading file '{file.metadata.name}' to blob '{blob_client.blob_name}' with metadata: {metadata}")
        return await blob_client.upload_blob(
            data=file.get_content(bytes),
            metadata=metadata,
            **kwargs,
        )

    def _merge_metadata(self, file: File, additional_metadata: Any | None) -> dict[str, Any]:
        metadata: dict[str, str] = {
            # name must be str() to avoid serialization issues, TODO: only on metadata save in blob, not on load
            "name": str(file.metadata.name),
            "rbac": AccessModel(category=file.metadata.category, roles=file.metadata.roles).model_dump_json(),
        }
        if file.metadata.language:
            metadata["language"] = file.metadata.language

        if not additional_metadata:
            return metadata

        if not isinstance(additional_metadata, dict):
            raise TypeError("metadata must be a dictionary")

        RESERVED_KEYS = {"name", "rbac", "language"}
        for key, value in additional_metadata.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError("Keyword argument 'metadata' must be of type dict[str, str]")
            if key in RESERVED_KEYS:
                continue
            metadata[key] = value

        return metadata
