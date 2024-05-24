from enum import auto
from enum import Enum
from typing import Any
from typing import Dict

from config import Config
from services.auth import OAuthService
from services.category import FacetCategoryService
from services.citation import RegexCitationService
from services.content import AzureBlobContentService
from services.feedback import FeedbackLogger
from services.language import LanguageProcessingService
from services.llm import OpenAIService
from services.logger import new_logger
from services.search import AzureSearchService

logger = new_logger(__name__)


class ServiceName(Enum):
    """ServiceName is an enumeration of all available service implementations."""

    OPEN_AI_SERVICE = auto()
    OAUTH_SERVICE = auto()
    FACET_CATEGORY_SERVICE = auto()
    REGEX_CITATION_SERVICE = auto()
    AZURE_BLOB_CONTENT_SERVICE = auto()
    FEEDBACK_LOGGER = auto()
    LANGUAGE_PROCESSING_SERVICE = auto()
    AZURE_SEARCH_SERVICE = auto()


class ServiceFactory:
    """ServiceFactory is a factory class that creates services."""

    def __init__(self, cfg: Config, clients: Dict[str, Any]):
        self.config = cfg
        self.clients = clients
        self.services: Dict[ServiceName, Any] = {}

    # We don't have a generic interface for services, so we need to return Any.
    # This is a limitation of the current design due to the lack of a common base class or interface for services.
    def get_service(self, service: ServiceName) -> Any:
        """get_service gets the service by name. If the service is not cached, it will be created.

        Raises:
            ValueError: If the service is not recognized.

        Returns:
            Any: The service. Always type cast the return value to the expected service type to ensure type safety.
        """
        if service in self.services:
            return self.services[service]

        match service:
            case ServiceName.OPEN_AI_SERVICE:
                logger.info("Creating LLM service")
                svc = OpenAIService(client=self.clients["LLMClient"])
            case ServiceName.OAUTH_SERVICE:
                logger.info("Creating Auth service")
                svc = OAuthService(
                    client=self.clients["AuthClient"],
                    cat_svc=self.get_service(ServiceName.FACET_CATEGORY_SERVICE),
                )
            case ServiceName.FACET_CATEGORY_SERVICE:
                logger.info("Creating Category service")
                svc = FacetCategoryService(search_client=self.clients["SearchClient"])
            case ServiceName.REGEX_CITATION_SERVICE:
                logger.info("Creating Citation service")
                svc = RegexCitationService()
            case ServiceName.AZURE_BLOB_CONTENT_SERVICE:
                logger.info("Creating Content service")
                svc = AzureBlobContentService(client=self.clients["StorageClient"])
            case ServiceName.FEEDBACK_LOGGER:
                logger.info("Creating Feedback service")
                svc = FeedbackLogger()
            case ServiceName.LANGUAGE_PROCESSING_SERVICE:
                logger.info("Creating language service")
                svc = LanguageProcessingService(
                    abbreviations=self.config.chat.abbreviations,
                )
            case ServiceName.AZURE_SEARCH_SERVICE:
                logger.info("Creating Search service")
                svc = AzureSearchService(
                    cfg=self.config.chat.settings.query,
                    search_client=self.clients["SearchClient"],
                    llm_svc=self.get_service(ServiceName.OPEN_AI_SERVICE),
                    lang_svc=self.get_service(ServiceName.LANGUAGE_PROCESSING_SERVICE),
                )
            case _:
                logger.error(f"Service {service} is not recognized.")
                raise ValueError(f"Service {service} is not recognized.")

        self.services[service] = svc
        return svc
