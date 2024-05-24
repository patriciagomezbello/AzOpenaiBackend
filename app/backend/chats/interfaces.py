from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional

from api.models import ChatMessage
from api.models import ChatResponse
from api.models import Overrides


ChatResponseType = ChatResponse


class ChatApproach(ABC):
    """ChatApproach is the interface for the chat approaches."""

    @abstractmethod
    async def run(self, history: List[ChatMessage], overrides: Optional[Overrides], roles: Optional[List[str]]) -> ChatResponseType:
        """run runs the chat approach."""
        ...


class AskApproach(ABC):
    """AskApproach is the interface for the ask approaches."""

    @abstractmethod
    async def run(self, question: str, overrides: Optional[Overrides]) -> ChatResponseType:
        """run runs the ask approach."""
        ...
