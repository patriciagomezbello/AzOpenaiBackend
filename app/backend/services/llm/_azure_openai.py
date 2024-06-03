from typing import List

from clients import LLMClient
from config import OpenAIConfig
from services.llm._interface import LLMService
from services.logger import new_logger
from services.messages.builder import Builder
from services.messages.builder import new_builder_with_instructions
from services.messages.tokenizer import Tokenizer
from services.schemas import ChatData
from services.schemas import CreateEmbeddingOptions
from services.schemas import Document
from services.schemas import LLMOptions
from services.schemas import Message
from services.schemas import Model
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
            builder.add_message(msg)
            if i == len(msgs) - 1 and options.enhanced_context and len(options.enhanced_context) > 0:
                logger.debug(f"Trying to add enhanced context to the last message with {len(options.enhanced_context)} documents")
                builder = self._add_enhanced_context(builder, options.enhanced_context)

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

    @timer()
    def _add_enhanced_context(self, builder: Builder, context: List[Document]) -> Builder:
        """_add_enhanced_context adds the enhanced context to the builder.
        It appends the context to the last message and evenly truncates the documents and messages
        if the token limit is exceeded.
        """
        if len(context) == 0:
            logger.debug("No documents to add to the builder")
            return builder

        total_tokens = builder.tokens() + builder.tokenizer.tokenize_documents(context) + Model.ANSWER_TOKEN_LIMIT
        token_limit = self.config().gpt.model.token_limit()

        if total_tokens <= token_limit:
            builder.add_documents(context)
            return builder

        excess_tokens = total_tokens - token_limit

        msg_tokens = [builder.tokenizer.tokenize_message(msg) for msg in builder.get_messages()]
        total_msg_tokens = sum(msg_tokens)
        total_doc_tokens = builder.tokenizer.tokenize_documents(context)

        if total_msg_tokens == 0 or total_doc_tokens == 0:
            raise ValueError("Total message or document tokens cannot be zero")

        msg_truncation_ratio, doc_truncation_ratio = self._calculate_truncation_ratios(total_msg_tokens, total_doc_tokens)
        logger.debug(f"Truncation ratios: messages={msg_truncation_ratio}, documents={doc_truncation_ratio}")

        builder, remaining_tokens = self._truncate_messages(builder, msg_tokens, int(excess_tokens * msg_truncation_ratio))
        logger.debug(f"Truncated messages to {len(builder.get_messages())} with {remaining_tokens} tokens remaining to truncate")

        doc_truncation_ratio = self._calculate_truncation_ratios(total_msg_tokens, total_doc_tokens + remaining_tokens)[1]
        logger.debug(f"Truncation ratio: documents={doc_truncation_ratio}")

        truncated_docs = self._truncate_documents(context, int(excess_tokens * doc_truncation_ratio), builder.tokenizer)
        logger.debug(f"Truncated {len(context) - len(truncated_docs)} documents")

        builder.add_documents(truncated_docs)
        logger.debug(
            f"Added {len(truncated_docs)} documents to the builder and the builder has {len(builder.get_messages())} messages "
            + f"with {builder.tokens()} tokens"
        )

        return builder

    def _calculate_truncation_ratios(self, total_msg_tokens: int, total_doc_tokens: int) -> tuple[float, float]:
        """_calculate_truncation_ratios calculates the truncation ratios for messages and documents."""
        total_tokens = total_msg_tokens + total_doc_tokens
        if total_tokens == 0:
            raise ValueError("Total tokens for the messages and documents are zero, cannot calculate truncation ratios.")

        msg_truncation_ratio = total_msg_tokens / total_tokens
        doc_truncation_ratio = total_doc_tokens / total_tokens
        return msg_truncation_ratio, doc_truncation_ratio

    def _truncate_messages(self, builder: Builder, msg_tokens: List[int], msg_tokens_to_truncate: int) -> tuple[Builder, int]:
        """_truncate_messages truncates messages to reduce the token count.
        If no more messages can be truncated, the function returns the builder with only one message and
        the remaining tokens to truncate.
        """

        truncated = 0
        # We go through the messages in reverse order to preserve the last user message
        for msg_token in reversed(msg_tokens):
            if msg_tokens_to_truncate <= 0:
                logger.debug(f"No more tokens to truncate, remaining tokens: {msg_tokens_to_truncate}")
                break

            if len(builder.get_messages()) <= 2:
                logger.debug("Cannot truncate the last message")
                break

            msg_tokens_to_truncate -= msg_token
            truncated += builder.truncate_messages(len(builder.get_messages()) - 1)

        logger.debug(f"Truncated {truncated} messages, {max(0, msg_tokens_to_truncate)} tokens remaining to truncate")
        return builder, max(0, msg_tokens_to_truncate)

    def _truncate_documents(self, context: List[Document], doc_tokens_to_truncate: int, tokenizer: Tokenizer) -> List[Document]:
        """_truncate_documents truncates documents to reduce the token count."""
        truncated_docs: List[Document] = []
        remaining_tokens = tokenizer.tokenize_documents(context) - doc_tokens_to_truncate

        for doc in context:
            doc_token_count = tokenizer.tokenize_documents([doc])
            if doc_token_count > remaining_tokens or remaining_tokens <= 0:
                logger.debug(f"Cannot add document with {doc_token_count} tokens, remaining tokens: {remaining_tokens}")
                break

            truncated_docs.append(doc)
            remaining_tokens -= doc_token_count

        return truncated_docs
