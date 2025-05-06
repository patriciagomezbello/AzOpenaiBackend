from dataclasses import dataclass
from dataclasses import field

from api.routes.legacy.models.chat_models import ChatMessageDict
from api.routes.legacy.models.chat_models import ChatMessageDTO


@dataclass
class FeedbackRequest:
    """FeedbackRequest is a class that holds the feedback request data."""

    history: list[ChatMessageDTO]
    rating: int
    message: str
    categories: list[str] = field(default_factory=list)

    def __post_init__(self):
        """__post_init__ is responsible for the deep conversion of the dataclass fields."""

        if isinstance(self.history, list):
            # fmt: off
            # Disabled formatting for better readability
            self.history = [
                ChatMessageDTO(**item) if isinstance(item, dict) else item
                for item in self.history
            ]
            # fmt: on

    def to_dict(self) -> dict[str, str | int | list[ChatMessageDict] | list[str]]:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "message": self.message,
            "rating": self.rating,
            "history": [item.to_dict() for item in self.history],
            "categories": self.categories,
        }


@dataclass
class FeedbackResponse:
    """FeedbackResponse is a class that holds the feedback response data."""

    response: str
