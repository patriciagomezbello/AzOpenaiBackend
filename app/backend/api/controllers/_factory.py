from api.controllers.base import Controller
from api.controllers.category import CategoryController
from api.controllers.chat import ChatController
from api.controllers.content import ContentController
from api.controllers.feedback import FeedbackController
from chats import ChatRegistry
from config import Config
from services.category import CategoryService
from services.factory import ServiceFactory
from services.factory import ServiceName
from services.logger import new_logger
from services.search import SearchService


logger = new_logger(__name__)


class Controllers:
    """Controllers is a class that holds all the controllers for the API."""

    def __init__(self, cfg: Config, svc_factory: ServiceFactory):
        self.cfg = cfg
        self.svc_factory = svc_factory
        self.setup_controllers()

    async def startup(self):
        """startup initializes the controllers and services."""

        cat_svc: CategoryService = self.svc_factory.get_service(ServiceName.FACET_CATEGORY_SERVICE)
        search_svcs: list[SearchService] = [
            self.svc_factory.get_service(ServiceName.AZURE_SEARCH_SERVICE),
            self.svc_factory.get_service(ServiceName.AZURE_EXTENDED_SEARCH_SERVICE),
            self.svc_factory.get_service(ServiceName.AZURE_FULL_SEARCH_SERVICE),
        ]

        for search_svc in search_svcs:
            try:
                await cat_svc.sync_facets(search_svc=search_svc)
                logger.info("Syncronized facets with search service")
            except Exception as e:
                logger.warning("Error while syncing facets with search service", {"error": str(e)}, exc_info=True)

    def setup_controllers(self) -> None:
        """setup_controllers initializes all the controllers."""

        Controller.initialize(cfg=self.cfg, auth=self.svc_factory.get_service(ServiceName.OAUTH_SERVICE))
        self.category = CategoryController(
            cat_svc=self.svc_factory.get_service(ServiceName.FACET_CATEGORY_SERVICE),
        )
        self.chat = ChatController(
            chat_registry=ChatRegistry(cfg=self.cfg, svc_factory=self.svc_factory),
        )
        self.content = ContentController(
            con_svc=self.svc_factory.get_service(ServiceName.AZURE_BLOB_CONTENT_SERVICE),
            search_svc=self.svc_factory.get_service(ServiceName.AZURE_SEARCH_SERVICE),
        )
        self.feedback = FeedbackController(
            feedback_svc=self.svc_factory.get_service(ServiceName.FEEDBACK_LOGGER),
        )
