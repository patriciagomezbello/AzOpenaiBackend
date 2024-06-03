from abc import ABC
from abc import abstractmethod
from typing import List

from services.schemas import Document
from services.schemas import Message
from services.schemas import Model
from tiktoken import encoding_for_model


class Tokenizer(ABC):
    """Tokenizer provides an interface for tokenizing messages."""

    @abstractmethod
    def tokenize_messages(self, msgs: List[Message]) -> int: ...

    @abstractmethod
    def tokenize_message(self, m: Message) -> int: ...

    @abstractmethod
    def tokenize_documents(self, docs: List[Document]) -> int: ...


class Tokenization(Tokenizer):
    """Tokenization tokenizes messages using the given model.
    Tokenization implements the Tokenizer interface.
    """

    def __init__(self, model: Model):
        self.model = model.parse()
        self.encoder = encoding_for_model(self.model)

    def tokenize_messages(self, msgs: List[Message]) -> int:
        """tokenize_messages calculates the number of tokens required to encode the given messages.

        Example:
            >>> msgs = [
                Message({"role": "user", "content": "Hello, how are you?"}),
                Message({"role": "assistant", "content": "I'm fine, thank you."}),
                Message({"role": "user", "content": "That's good to hear."})
                ]
            >>> tokenizer.tokenize_messages(msgs) # Returns 23

        For more information, refer to https://platform.openai.com/tokenizer or the tiktoken documentation.
        """
        num = 0
        for m in msgs:
            num += self.tokenize_message(m)
        return num

    def tokenize_message(self, m: Message) -> int:
        """_num_tokens_for_message calculates the number of tokens required to encode the given message."""
        num = 2  # Initalize with 2 tokens for the message dictionary keys
        num += len(self.encoder.encode(m.role()))
        num += len(self.encoder.encode(m.content()))
        return num

    def tokenize_documents(self, docs: List[Document]) -> int:
        """tokenize_document calculates the number of tokens required to encode the given document."""
        num = 0
        for doc in docs:
            num += len(self.encoder.encode(str(doc)))
        return num
