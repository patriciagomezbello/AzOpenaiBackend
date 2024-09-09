from abc import abstractmethod
from typing import Awaitable

from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import get_bearer_token_provider
from config import OpenAIConfig
from dependency_injector import resources
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion
from openai.types.create_embedding_response import CreateEmbeddingResponse
from services.logger import new_logger
from services.schemas import ChatCompletionsOptions
from services.schemas import CreateEmbeddingOptions


logger = new_logger(__name__)


class LLMClient(resources.AsyncResource):
    """LLMClient provides an interface for interacting with the large language model."""

    @abstractmethod
    def create_completion(self, opts: ChatCompletionsOptions) -> Awaitable[ChatCompletion]:
        """create_completion generates a response based on the provided options.

        If no model is provided, the configuration completion model is used.
        """
        ...

    @abstractmethod
    def create_embedding(self, opts: CreateEmbeddingOptions) -> Awaitable[CreateEmbeddingResponse]:
        """create_embedding creates an embedding vector representing the input text.

        If no model is provided, the configuration embedding model is used.
        """
        ...

    @abstractmethod
    def config(self) -> OpenAIConfig:
        """config returns the LLM client configuration."""
        ...


class OpenAIClient(LLMClient):
    """OpenAIClient is a client for the (Azure) OpenAI API.
    It implements the LLMClient interface.
    """

    # API_VERSION is the version of the OpenAI API to use.
    API_VERSION = "2023-07-01-preview"

    async def init(self, config: OpenAIConfig, credentials: ChainedTokenCredential):
        endpoint = f"https://{config.service}.openai.azure.com"
        token_provider = get_bearer_token_provider(
            credentials,
            "https://cognitiveservices.azure.com/.default",
        )

        self.client = AsyncAzureOpenAI(
            api_version=self.API_VERSION,
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
        )
        self.cfg = config
        return self

    def create_completion(self, opts: ChatCompletionsOptions) -> Awaitable[ChatCompletion]:
        """create_completion generates a response based on the provided options."""

        if opts.messages is None:
            # This should never be the case since the LLM service should inject the messages
            # However, we need to handle this case to avoid a type error
            opts.messages = []

        if opts.model is None:
            opts.model = self.cfg.gpt.deployment

        return self.client.chat.completions.create(
            messages=opts.messages,
            model=opts.model,
            temperature=opts.temperature,
            max_tokens=opts.max_tokens,
            n=opts.n,
            top_p=opts.top_p,
            frequency_penalty=opts.frequency_penalty,
            presence_penalty=opts.presence_penalty,
            stop=opts.stop,
        )

    def create_embedding(self, opts: CreateEmbeddingOptions) -> Awaitable[CreateEmbeddingResponse]:
        """create_embedding creates an embedding vector representing the input text."""

        if opts.input is None:
            # This should never be the case since the search or LLM service should inject the input
            # However, we need to handle this case to avoid a type error
            opts.input = []

        if opts.model is None:
            opts.model = self.cfg.gpt.embed_deployment

        return self.client.embeddings.create(
            model=opts.model,
            input=opts.input,
            timeout=opts.timeout,
        )

    def config(self) -> OpenAIConfig:
        """config returns the OpenAI client configuration."""
        return self.cfg

    async def shutdown(self, _: None) -> None:
        """shutdown closes the OpenAI client's connection.

        After calling this method, the client is no longer usable.
        """
        await self.client.close()
