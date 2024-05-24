from abc import ABC
from abc import abstractmethod

from api.models import FeedbackRequest


__all__ = ["FeedbackService"]


class FeedbackService(ABC):
    """FeedbackService provides an interface for interacting with the feedback service."""

    @abstractmethod
    async def send_feedback(self, feedback: FeedbackRequest) -> None:
        """send_feedback sends the feedback."""
        ...
