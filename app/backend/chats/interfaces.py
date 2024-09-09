from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from api.models import Overrides


ChatMessageDict = dict[str, str | None]


@dataclass
class ChatMessage:
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
class DataPoint:
    """DataPoint represents a citation data point."""

    docName: str
    page: int | None


@dataclass
class ChatResponse:
    """ChatResponse represents the chat response data."""

    answer: str
    keywords: str
    data_points: list[DataPoint]


class ChatApproach(ABC):
    """ChatApproach is the interface for the chat approaches."""

    @abstractmethod
    async def run(
        self,
        history: list[ChatMessage],
        overrides: Overrides | None,
        roles: list[str] | None,
    ) -> ChatResponse:
        """run runs the chat approach."""
        ...
