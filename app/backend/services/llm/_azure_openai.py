from typing import List

from clients import LLMClient
from config import OpenAIConfig
from services.llm._interface import LLMService
from services.logger import new_logger
from services.messages.builder import Builder
from services.messages.builder import new_builder_with_instructions
from services.schemas import ChatData
from services.schemas import CreateEmbeddingOptions
from services.schemas import LLMOptions
from services.schemas import Message
from services.timer import timer


logger = new_logger(__name__)


class OpenAIService(LLMService):
    """OpenAIService provides an implementation of the AI service interface.

    Args:
        client (AIClient): The OpenAI client to use for interacting with the API.
    """

    def __init__(self, client: LLMClient):
        self.client = client

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

        if len(msgs) == 0:
            raise ValueError("No messages provided")

        if options.chat.max_tokens is None:
            raise ValueError("max_tokens must be set in options")

        if options.context_prompt is not None:
            return await self._generate_with_context(msgs, options)

        return await self._generate(msgs, options)

    @timer()
    async def create_embedding(self, text: str, options: CreateEmbeddingOptions) -> List[float]:
        """create_embedding creates an embedding vector representing the input text.

        Args:
            text (str): The text to embed, this overrides the input field in the options.
            options (CreateEmbeddingOptions): Options for the embedding request.

        Returns:
            List[float]: A list of floats representing the embedding vector.
        """

        options.input = text.replace("\n", " ")
        resp = await self.client.create_embedding(opts=options)
        return resp.data[0].embedding

    def config(self) -> OpenAIConfig:
        """config returns the OpenAI client configuration."""
        return self.client.config()

    @timer()
    async def _generate_with_context(self, msgs: List[Message], options: LLMOptions) -> str:
        """_generate_with_context generates a response with a context prompt.
        The context prompt is formatted with the provided data.

        Example:
            >>> "Translate the following text to {language}." -> "Translate the following text to French."
        """

        if options.context_prompt is None:
            # This should never be the case since we check for it in the generate method
            # However, we need to handle this case to avoid a type error
            raise ValueError("No context prompt provided")

        instructions = self._format_context_prompt(options.context_prompt.template, options.context_prompt.data)

        builder: Builder = new_builder_with_instructions(instructions=instructions, model=self.config().gpt.model)

        for i, msg in enumerate(msgs):
            if options.enhanced_context and options.enhanced_context != "" and i == len(msgs) - 1:
                msg.set_content(f"{msg.content()}\n\nSources:\n{options.enhanced_context}")
            builder.add_message(msg)

        options.chat.messages = builder.build()
        resp = await self.client.create_completion(opts=options.chat)

        if resp.choices[0].message.content is None:
            raise ValueError("No response generated")

        if resp.usage:
            logger.debug(({"model": resp.model, "usage": resp.usage.model_dump()}))

        return resp.choices[0].message.content

    @timer()
    async def _generate(self, msgs: List[Message], options: LLMOptions) -> str:
        """_generate generates a response without a context prompt."""

        options.chat.messages = [msg.to_chat_request_message() for msg in msgs]
        resp = await self.client.create_completion(opts=options.chat)

        if resp.choices[0].message.content is None:
            raise ValueError("No response generated")

        return resp.choices[0].message.content

    def _format_context_prompt(self, template: str, data: ChatData) -> str:
        """_format_context_prompt formats the context prompt with the provided data."""

        return template.format(**data.to_dict())
