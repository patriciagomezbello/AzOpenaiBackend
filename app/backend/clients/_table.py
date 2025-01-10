from abc import abstractmethod

from azure.core.async_paging import AsyncItemPaged
from azure.data.tables import TableEntity
from azure.data.tables.aio import TableServiceClient
from azure.identity.aio import ChainedTokenCredential
from config import TableConfig
from dependency_injector import resources
from services.logger import new_logger


logger = new_logger(__name__)


class TableClient(resources.AsyncResource):
    """TableClient provides an interface for interacting with a table service."""

    @abstractmethod
    def get_all(self) -> list[TableEntity]:
        """get_all downloads all the entities from the table."""
        ...

    @abstractmethod
    def get_entity(self, partition_key: str) -> TableEntity:
        """get_entity gets the entity with the specified partition key."""
        ...

    @abstractmethod
    def insert_entity(self, entity: TableEntity) -> None:
        """insert_entity inserts the specified entity into the table."""
        ...


class AzureTableClient(TableClient):
    """AzureTableClient is a client for Tables in an azure storage.
    It implements the TableClient interface.
    """

    async def init(self, cfg: TableConfig, credentials: ChainedTokenCredential):
        self.client = TableServiceClient(
            endpoint=f"https://{cfg.account}.table.core.windows.net",
            credential=credentials,
        )
        try:
            self.table_client = self.client.get_table_client(cfg.table_name)
        except Exception as e:
            logger.error(f"Error creating table client: {e}")
        self.cfg = cfg
        return self

    async def get_all(self) -> AsyncItemPaged[TableEntity]:
        """get_all downloads all the entities from the table."""
        try:
            all_prompts = self.table_client.list_entities()
        except Exception as e:
            logger.error(f"Error getting all entities: {e}")
            raise e
        return all_prompts

    async def get_entity(self, partition_key: str) -> TableEntity:
        """get_entity gets the entity with the specified partition key."""
        return await self.table_client.get_entity(partition_key=partition_key, row_key=partition_key)

    async def insert_entity(self, entity: TableEntity) -> None:
        """insert_entity inserts the specified entity into the table."""
        try:
            await self.table_client.upsert_entity(entity=entity)
        except Exception as e:
            logger.error(f"Error inserting entity: {e}")

    async def shutdown(self, _: None) -> None:
        """shutdown closes the storage client's connection.

        After calling this method, the client is no longer usable.
        """
        await self.client.close()
        await self.table_client.close()
