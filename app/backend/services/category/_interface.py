from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional

from services.search import SearchService


__all__ = ["CategoryService"]


class CategoryService(ABC):
    """CategoryService provides an interface for interacting with the category service."""

    @abstractmethod
    async def get_categories(self, roles: Optional[List[str]]) -> List[str]:
        """get_categories returns a list of categories."""
        ...

    @abstractmethod
    async def sync_facets(self, search_svc: SearchService) -> None:
        """sync_facets syncronizes the local facets with the ones in the search index."""
        ...
