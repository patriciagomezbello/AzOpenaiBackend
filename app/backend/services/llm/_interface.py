from abc import ABC
from abc import abstractmethod
from typing import List

from config.appconfig import OpenAIConfig
from services.schemas import CreateEmbeddingOptions
from services.schemas import LLMOptions
from services.schemas import Message


class LLMService(ABC):
    """LLMService provides an interface for interacting with the large language model service."""

    @abstractmethod
    async def generate(self, msgs: List[Message], options: LLMOptions) -> str:
        """generate generates a response based on the provided messages and options.

        Args:
            msgs (List[Message]): The messages (chat history) to generate a response from.
            options (Options): Options for the generation request.

        Raises:
            ValueError: If no messages are provided or max_tokens is not set in options.

        Returns:
            str: The generated response.
        """
        ...

    @abstractmethod
    async def create_embedding(self, text: str, options: CreateEmbeddingOptions) -> List[float]:
        """create_embedding creates an embedding vector representing the input text.

        Args:
            text (str): The text to embed, this overrides the input field in the options.
            options (CreateEmbeddingOptions): Options for the embedding request.

        Returns:
            List[float]: A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    def config(self) -> OpenAIConfig:
        """config returns the OpenAI client configuration."""
        ...
