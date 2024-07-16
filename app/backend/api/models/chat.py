from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import List
from typing import Optional

from api.models.common import ChatMessage
from api.models.common import DataPoint
from api.models.common import Overrides


@dataclass
class ChatRequest:
    """ChatRequest represents the chat request data."""

    history: List[ChatMessage] = field(default_factory=list)
    approach: str = "rrr"
    overrides: Optional[Overrides] = None

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
    data_points: List[DataPoint]
