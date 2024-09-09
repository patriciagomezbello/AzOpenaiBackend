from dataclasses import dataclass
from dataclasses import field
from typing import Any

from api.models.common_models import Overrides

ChatMessageDict = dict[str, str | None]


@dataclass
class ChatMessageDTO:
    """ChatMessage represents a chat message.
    A chat message always contains a user message and may contain a bot response
    to that message.
    It can also contain the model used to generate the bot response.
    """

    user: str
    bot: str | None = None
    model: str | None = None

    def to_dict(self) -> ChatMessageDict:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "user": self.user,
            "bot": self.bot,
            "model": self.model,
        }


@dataclass
class DataPointDTO:
    """DataPoint represents a citation data point."""

    docName: str
    page: int | None


@dataclass
class ChatRequest:
    """ChatRequest represents the chat request data."""

    history: list[ChatMessageDTO] = field(default_factory=list)
    approach: str = "rrr"
    overrides: Overrides | None = None

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

        if isinstance(self.overrides, dict):
            valid_attrs: dict[str, Any] = {k: v for k, v in self.overrides.items() if k in Overrides.__dataclass_fields__.keys()}
            self.overrides = Overrides(**valid_attrs)

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "history": ([msg.to_dict() for msg in self.history] if include_sensitive else "REDACTED"),
            "approach": self.approach,
            "overrides": self.overrides.to_dict() if self.overrides else None,
        }

    def validate(self) -> bool:
        """validate checks if the chat request is valid."""
        return not self.history or not self.approach


@dataclass
class ChatResponse:
    """ChatResponse represents the chat response data."""

    answer: str
    keywords: str
    data_points: list[DataPointDTO]
