from services.feedback._interface import Feedback
from services.feedback._interface import FeedbackService
from services.logger import new_logger
from services.timer import timer


logger = new_logger(__name__)


class FeedbackLogger(FeedbackService):
    """FeedbackLogger provides a service for sending feedback."""

    @timer()
    async def send_feedback(self, feedback: Feedback) -> None:
        """send_feedback sends the feedback to the service."""

        # This indirectly sends the feedback to the application insights service of azure
        # which will process the feedback further.
        logger.info("Feedback received", {"feedback": feedback.to_dict()})
        return
