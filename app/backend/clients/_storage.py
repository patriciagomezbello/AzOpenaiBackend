from abc import abstractmethod
from typing import Awaitable

from azure.identity.aio import ChainedTokenCredential
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob.aio import StorageStreamDownloader
from config import StorageConfig
from dependency_injector import resources
from services.logger import new_logger


logger = new_logger(__name__)


class StorageClient(resources.AsyncResource):
    """StorageClient provides an interface for interacting with a storage service."""

    @abstractmethod
    def download(self, path: str) -> Awaitable[StorageStreamDownloader]:
        """download downloads the file at the specified path from the storage.

        The returned downloader can be used to read the file's content.
        """
        ...


class AzureStorageClient(StorageClient):
    """AzureStorageClient is a client for the Azure Blob Storage.
    It implements the StorageClient interface.
    """

    async def init(self, cfg: StorageConfig, credentials: ChainedTokenCredential):
        self.client = BlobServiceClient(
            account_url=f"https://{cfg.account}.blob.core.windows.net",
            credential=credentials,
        )
        self.container_client = self.client.get_container_client(cfg.container)
        self.cfg = cfg
        return self

    def download(self, path: str) -> Awaitable[StorageStreamDownloader[bytes]]:
        """download downloads the file at the specified path from the storage.

        The returned downloader can be used to read the file's content.
        """
        blob_client = self.container_client.get_blob_client(path)
        return blob_client.download_blob()

    async def shutdown(self, _: None) -> None:
        """shutdown closes the storage client's connection.

        After calling this method, the client is no longer usable.
        """
        await self.client.close()
        await self.container_client.close()
