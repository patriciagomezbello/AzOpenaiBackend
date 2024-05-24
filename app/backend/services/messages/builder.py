from typing import List

from openai.types.chat import ChatCompletionMessageParam
from services.logger import new_logger
from services.messages.tokenizer import Tokenization
from services.messages.tokenizer import Tokenizer
from services.schemas import Message
from services.schemas import Model


logger = new_logger(__name__)


class Builder:
    """Builder is used to construct a list of messages that can be used to generate a chat completion."""

    def __init__(self, model: Model):
        self.tokenizer: Tokenizer = Tokenization(model)
        self.num_tokens: int = 0
        self.messages: list[Message] = []

    def add_message(self, message: Message):
        """add_message adds a message to the builder.

        Example:
            >>> from services.messages import Message, Model, Builder
            >>> model = Model("gpt-3.5-turbo")
            >>> b = Builder(model)
            >>> b.add_message(Message({"role": Message.SYSTEM_ROLE, "content": "Hello, how can I help you today?"}))
        """

        self.messages.append(message)
        self.num_tokens += self.tokenizer.tokenize_messages([message])

    def get_messages(self) -> list[Message]:
        """get_messages returns the messages in the builder."""
        return self.messages

    def build(self) -> List[ChatCompletionMessageParam]:
        """build returns the messages in the builder as a list of ChatCompletionMessageParam objects."""

        return [m.to_chat_request_message() for m in self.messages]

    def tokens(self) -> int:
        """tokens returns the number of tokens in the builder."""
        return self.num_tokens


def new_builder_with_instructions(model: Model, instructions: str) -> Builder:
    """new_builder_with_instructions creates a new Builder with a system message containing instructions for the AI."""

    b = Builder(model)
    b.add_message(Message({"role": Message.SYSTEM_ROLE, "content": instructions}))
    return b
