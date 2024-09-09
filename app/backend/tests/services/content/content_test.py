import unittest
from io import BytesIO
from unittest.mock import AsyncMock
from unittest.mock import patch

from services.content import AzureBlobContentService


class TestContentService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_client = AsyncMock()
        self.service = AzureBlobContentService(self.mock_client)

    async def test_get_file_success(self):
        """Test successful file retrieval."""

        path = "test/file.txt"
        want_mimetype = "text/plain"
        want_content = b"Hello, World!"

        downloader_mock = AsyncMock()
        downloader_mock.properties = {"content_settings": {"content_type": want_mimetype}}
        downloader_mock.readinto = AsyncMock()

        async def readinto_mock(buffer: BytesIO) -> int:
            buffer.write(want_content)
            return len(want_content)

        downloader_mock.readinto.side_effect = readinto_mock
        self.mock_client.download.return_value = downloader_mock

        file = await self.service.get_file(path)
        self.assertEqual(file.name, path)
        self.assertEqual(file.mimetype, want_mimetype)
        self.assertEqual(file.data.getvalue(), want_content)

    async def test_get_file_not_found(self):
        """Test file retrieval when file does not exist."""

        path = "nonexistent/file.txt"
        self.mock_client.download.side_effect = FileNotFoundError("File not found")

        with self.assertRaises(FileNotFoundError):
            await self.service.get_file(path)

    async def test_unexpected_exception(self):
        """Test unexpected exception during file retrieval."""

        path = "test/file.txt"
        self.mock_client.download.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception) as context:
            await self.service.get_file(path)
        self.assertIn("Unexpected error", str(context.exception))

    async def test_mime_type_resolution(self):
        """Test MIME type resolution for application/octet-stream."""

        path = "test/file"
        expected_content = b"binary data"
        downloader_mock = AsyncMock()
        downloader_mock.properties = {"content_settings": {"content_type": "application/octet-stream"}}
        downloader_mock.readinto = AsyncMock()

        async def readinto_mock(buffer):
            buffer.write(expected_content)
            return len(expected_content)

        downloader_mock.readinto.side_effect = readinto_mock
        self.mock_client.download.return_value = downloader_mock
        with patch("mimetypes.guess_type", return_value=("binary/octet-stream", None)):
            file = await self.service.get_file(path)
            self.assertEqual(file.mimetype, "binary/octet-stream")


if __name__ == "__main__":
    unittest.main()
