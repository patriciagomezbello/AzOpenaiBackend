from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional

from api.models import Overrides
from lingua import Language
from services.schemas import ChatData
from services.schemas import Document
from services.schemas import Facet
from services.schemas import Message


__all__ = ["SearchService"]


class SearchService(ABC):
    """SearchService provides an interface for interacting with the search service."""

    @abstractmethod
    async def build_query_prompt(self, msgs: List[Message], data: ChatData) -> str:
        """build_query_prompt builds a query prompt for the given messages and chat (meta)data.

        Raises:
            ValueError: If the query prompt cannot be built.

        Returns:
            str: The query prompt.
        """
        ...

    @abstractmethod
    async def cognitive_search(
        self, search_query: str, overrides: Overrides, lang: Language, roles: Optional[List[str]]
    ) -> List[Document]:
        """cognitive_search performs a cognitive search based on the provided query and overrides.

        Raises:
            ValueError: If the search fails.

        Returns:
            str: The search results.
        """
        ...

    @abstractmethod
    def initialize_search_index(self, doclangs: List[Facet]) -> None:
        """initialize_search_index sets the local facets based on the provided facets."""
        ...
