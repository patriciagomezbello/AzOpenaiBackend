import datetime
import importlib
from typing import Any
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableEntity
from clients._table import AzureTableClient
from services.logger import new_logger
from services.prompts._interface import PromptService
from services.schemas import NewPrompt
from services.schemas import SavedPrompt
from services.schemas import UpdatePrompt

logger = new_logger(__name__)


def _safe_import(module: str, name: str) -> Optional[Any]:
    """_safe_import imports the module and returns the attribute with the given name.
    Returns None if the module or attribute does not exist."""
    try:
        mod = importlib.import_module(module)
        return getattr(mod, name)
    except ImportError:
        return None
    except AttributeError:
        return None


system_message_chat_conversation: Optional[str] = _safe_import("core.context", "system_message_chat_conversation")


class InvalidConfigError(Exception):
    """InvalidConfigError is an error that is raised when the configuration is invalid."""


class PromptNotFoundError(Exception):
    """PromptNotFoundError is an error that is raised when the prompt is not found."""


class AzurePromptService(PromptService):

    def __init__(self, client: AzureTableClient):
        self.client = client

    async def get_prompts(self) -> list[SavedPrompt]:
        prompts_dict = []
        try:
            all_prompts = await self.client.get_all()
            async for prompt in all_prompts:
                prompts_dict.append(
                    SavedPrompt(
                        key=prompt.get("PartitionKey", ""),
                        name=prompt.get("PromptName", ""),
                        prompt=prompt.get("Prompt", ""),
                    )
                )
        except ResourceNotFoundError as e:
            if "ErrorCode:TableNotFound" in e.message:
                logger.warning("Table not found. Creating table")
                await self._create_table()
                prompts_dict = []
            elif "ErrorCode:ResourceNotFound" in e.message:
                logger.error("Table entity not found", {"error": str(e)})
                raise PromptNotFoundError()
            else:
                raise

        except Exception as e:
            logger.exception("Error while getting prompts", {"error": str(e)})
            raise InvalidConfigError("Error while getting prompts")

        return prompts_dict

    async def get_prompt(self, key: str) -> str:
        """get_prompt gets the prompt for the given key."""
        try:
            prompt = await self.client.get_entity(partition_key=key)
        except ResourceNotFoundError as e:
            if "ErrorCode:TableNotFound" in e.message:
                logger.warning("Table not found. Creating table")
                await self._create_table()
                prompt = None

            elif "ErrorCode:ResourceNotFound" in e.message:
                logger.error("Table entity not found", {"error": str(e)})
                raise PromptNotFoundError()

        if prompt:
            return prompt.get("Prompt", "")
        raise PromptNotFoundError()

    async def create_prompt(self, prompt: NewPrompt) -> None:
        """create_prompt creates a new prompt in the storage account table."""
        prompts = await self.get_prompts()
        max_partition_key = 0
        if len(prompts) > 0:
            max_partition_key = max(int(p.key) for p in prompts)

        data = TableEntity(
            {
                "PartitionKey": str(max_partition_key + 1),
                "RowKey": str(max_partition_key + 1),
                "Timestamp": datetime.datetime.now().isoformat(),
                "PromptName": prompt.name,
                "Prompt": prompt.prompt,
            }
        )
        try:
            await self.client.insert_entity(data)
        except Exception as e:
            logger.exception("Error while creating prompt", {"error": str(e)})
            raise InvalidConfigError("Error while creating prompt")

    async def _create_table(self) -> None:
        """create_table creates the table in the storage account."""
        try:
            await self.client.table_client.create_table()
        except Exception as e:
            raise InvalidConfigError(f"Error while creating table: {str(e)}")

    async def update_prompt(self, prompt: UpdatePrompt) -> None:
        """update_prompt updates the prompt in the storage account table."""
        try:
            await self.client.table_client.update_entity(
                entity={
                    "PartitionKey": prompt.key,
                    "RowKey": prompt.key,
                    "Timestamp": datetime.datetime.now().isoformat(),
                    "PromptName": prompt.name,
                    "Prompt": prompt.prompt,
                }
            )
        except Exception as e:
            logger.exception("Error while updating prompt", {"error": str(e)})
            raise InvalidConfigError("Error while updating prompt")

    async def delete_prompt(self, key: str) -> None:
        """delete_prompt deletes the prompt in the storage account table."""
        try:
            await self.client.table_client.delete_entity(partition_key=key, row_key=key)
        except ResourceNotFoundError as e:
            if "ErrorCode:ResourceNotFound" in e.message:
                logger.error("Table entity not found", {"error": str(e)})
                raise PromptNotFoundError()
        except Exception as e:
            logger.exception("Error while deleting prompt", {"error": str(e)})
            raise InvalidConfigError("Error while deleting prompt")
