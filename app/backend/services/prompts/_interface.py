from abc import ABC
from abc import abstractmethod

from services.schemas import NewPrompt

__all__ = ["PromptService"]


class PromptService(ABC):
    """ContentService is an interface for interacting with the content service."""

    @abstractmethod
    async def get_prompts(self) -> list[dict]:
        """get_prompts returns the list of prompts from the storage account table."""
        ...

    @abstractmethod
    async def get_prompt(self, key: str) -> str:
        """get_prompt gets the prompt for the given key."""
        ...

    @abstractmethod
    async def create_prompt(self, prompt: NewPrompt) -> None:
        """create_prompt creates a new prompt in the storage account table."""
        ...
