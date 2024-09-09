from abc import abstractmethod
from typing import Awaitable
from typing import Dict
from typing import List

from azure.identity.aio import ChainedTokenCredential
from azure.search.documents.aio import AsyncSearchItemPaged
from azure.search.documents.aio import SearchClient as Searcher
from config import SearchConfig
from dependency_injector import resources
from services.logger import new_logger
from services.schemas import SearchOptions


logger = new_logger(__name__)


class SearchClient(resources.AsyncResource):
    """SearchClient provides an interface for interacting with the search service."""

    @abstractmethod
    def search(self, opts: SearchOptions) -> Awaitable[AsyncSearchItemPaged[Dict]]:
        """search searches the index for the provided options."""
        ...

    @abstractmethod
    async def get_documents(self, keys: List[str]) -> List[Dict]:
        """get_documents retrieves the documents with the provided keys."""
        ...

    @abstractmethod
    async def get_document_count(self) -> int:
        """get_document_count retrieves the amount of documents indexed."""
        ...


class AzureSearchClient(SearchClient):
    """AzureSearchClient is a client for the Azure Search Service.
    It implements the SearchClient interface.
    """

    async def init(self, config: SearchConfig, credentials: ChainedTokenCredential):
        self.client = Searcher(
            endpoint=f"https://{config.service}.search.windows.net",
            index_name=config.index,
            credential=credentials,
        )
        return self

    def search(self, opts: SearchOptions) -> Awaitable[AsyncSearchItemPaged[Dict]]:
        """search searches the index for the provided options."""
        return self.client.search(
            search_text=opts.search_text,
            filter=opts.filter,
            query_type=opts.query_type,
            semantic_configuration_name=opts.semantic_configuration_name,
            top=opts.top,
            facets=opts.facets,
            order_by=opts.order_by,
            include_total_count=opts.include_total_count,
            query_caption=opts.query_caption,
            vector_queries=opts.vector_queries,
        )

    async def get_documents(self, keys: List[str]) -> List[Dict]:
        """get_documents retrieves the documents with the provided keys."""
        return [await self.client.get_document(key) for key in keys]

    async def get_document_count(self) -> int:
        """get_document_count retrieves the amount of documents indexed."""
        return await self.client.get_document_count()

    async def shutdown(self, _: None) -> None:
        """shutdown closes the search client's connection.

        After calling this method, the client is no longer usable.
        """
        await self.client.close()
