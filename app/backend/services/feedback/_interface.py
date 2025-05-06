from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Union

from chats.interfaces import ChatMessage
from chats.interfaces import ChatMessageDict


__all__ = ["FeedbackService"]


@dataclass
class Feedback:
    """Feedback is a class that holds the feedback request data."""

    history: List[ChatMessage]
    rating: int
    message: str
    categories: List[str] = field(default_factory=list)

    def __post_init__(self):
        """__post_init__ is responsible for the deep conversion of the dataclass fields."""

        if isinstance(self.history, list):
            # fmt: off
            # Disabled formatting for better readability
            self.history = [
                ChatMessage(**item) if isinstance(item, dict) else item
                for item in self.history
            ]
            # fmt: on

    def to_dict(self) -> dict[str, Union[str, int, list[ChatMessageDict], list[str]]]:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "message": self.message,
            "rating": self.rating,
            "history": [item.to_dict() for item in self.history],
            "categories": self.categories,
        }


class FeedbackService(ABC):
    """FeedbackService provides an interface for interacting with the feedback service."""

    @abstractmethod
    async def send_feedback(self, feedback: Feedback) -> None:
        """send_feedback sends the feedback."""
        ...
