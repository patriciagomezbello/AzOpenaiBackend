from dataclasses import dataclass
from dataclasses import field
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
            self.overrides = Overrides(**self.overrides)

    def validate(self) -> bool:
        """validate checks if the chat request is valid."""
        return not self.history or not self.approach


@dataclass
class ChatResponse:
    """ChatResponse represents the chat response data."""

    answer: str
    keywords: str
    data_points: List[DataPoint]
