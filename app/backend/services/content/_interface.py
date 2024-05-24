from abc import ABC
from abc import abstractmethod

from services.schemas import File


__all__ = ["ContentService"]


class ContentService(ABC):
    """ContentService is an interface for interacting with the content service."""

    @abstractmethod
    async def get_file(self, path: str) -> File:
        """get_file returns the file at the specified path from the blob storage."""
        ...
