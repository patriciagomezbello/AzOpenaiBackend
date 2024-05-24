from typing import Callable
from typing import Optional

from chats.interfaces import AskApproach
from chats.interfaces import ChatApproach
from chats.readretrieveread import ChatReadRetrieveRead
from config import Config
from services.factory import ServiceFactory


class ChatRegistry:
    """ChatRegistry holds the chat approaches."""

    # CHAT_REGISTRY holds all available chat approaches.
    # The key is the approach name and the value is the approach constructor.
    CHAT_REGISTRY: dict[str, Callable[[Config, ServiceFactory], ChatApproach]] = {
        "rrr": ChatReadRetrieveRead,
    }

    def __init__(self, cfg: Config, svc_factory: ServiceFactory):
        self._registry: dict[str, ChatApproach] = {}
        for key, approach in self.CHAT_REGISTRY.items():
            self._registry[key] = approach(cfg, svc_factory)

    def get(self, key: str) -> Optional[ChatApproach]:
        """get gets the chat approach by key."""
        return self._registry.get(key)


class AskRegistry:
    """AskRegistry holds the ask approaches."""

    # ASK_REGISTRY holds all available ask approaches.
    # The key is the approach name and the value is the approach constructor.
    ASK_REGISTRY: dict[str, Callable[[Config, ServiceFactory], AskApproach]] = {}

    def __init__(self, cfg: Config, svcs: ServiceFactory):
        self._registry: dict[str, AskApproach] = {}
        for key, approach in self.ASK_REGISTRY.items():
            self._registry[key] = approach(cfg, svcs)

    def get(self, key: str) -> Optional[AskApproach]:
        """get gets the ask approach by key."""
        return self._registry.get(key)
