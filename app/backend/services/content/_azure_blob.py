import mimetypes
from io import BytesIO

from clients import StorageClient
from services.content._interface import ContentService
from services.logger import new_logger
from services.schemas import File
from services.timer import timer


logger = new_logger(__name__)


class AzureBlobContentService(ContentService):
    """AzureBlobContentService is a service that provides access to files in the blob storage."""

    def __init__(self, client: StorageClient):
        self.client = client

    @timer()
    async def get_file(self, path: str) -> File:
        """get_file returns the file at the specified path from the blob storage."""

        try:
            downloader = await self.client.download(path)
        except Exception as e:
            logger.exception("Error while downloading file", {"path": path, "error": str(e)})
            raise FileNotFoundError(f"File not found: {path}")

        if not downloader.properties or not downloader.properties.has_key("content_settings"):
            logger.debug("Downloaded file has no content settings", {"path": path})
            raise FileNotFoundError(f"File not found: {path}")

        mimetype: str = downloader.properties["content_settings"]["content_type"]
        if mimetype == "application/octet-stream":
            mimetype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        content = BytesIO()
        await downloader.readinto(content)
        content.seek(0)
        return File(name=path, mimetype=mimetype, data=content)
