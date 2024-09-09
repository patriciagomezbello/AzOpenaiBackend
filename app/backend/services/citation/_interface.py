from abc import ABC
from abc import abstractmethod
from typing import List

from chats.interfaces import DataPoint


__all__ = ["CitationService"]


class CitationService(ABC):
    """CitationService provides an interface for interacting with the citation service."""

    @abstractmethod
    def get_citations(self, text: str) -> List[DataPoint]:
        """get_citations extracts citation information from the given text and
        returns a list of citations without duplicates."""
        ...
