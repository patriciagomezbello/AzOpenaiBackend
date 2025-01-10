from chats.interfaces import ChatApproach
from chats.readretrieveread import ChatReadRetrieveRead
from config import Config
from services.citation._interface import CitationService
from services.language._service import LanguageProcessingService
from services.llm._interface import LLMService
from services.prompts._azure_blob import AzurePromptService
from services.search._azure_search import AzureExtendedSearchService
from services.search._azure_search import AzureFullSearchService
from services.search._azure_search import AzureSearchService


class ChatRegistry:
    """ChatRegistry holds the chat approaches."""

    def __init__(
        self,
        cfg: Config,
        azure_search_service: AzureSearchService,
        azure_extended_service: AzureExtendedSearchService,
        azure_full_search_service: AzureFullSearchService,
        language_service: LanguageProcessingService,
        llm_service: LLMService,
        citation_service: CitationService,
        prompt_service: AzurePromptService,
    ) -> None:
        # _registry holds all available chat approaches.
        # The key is the approach name and the value is the approach constructor.
        self._registry: dict[str, ChatApproach] = {
            "rrr": ChatReadRetrieveRead(
                cfg=cfg,
                azure_search_service=azure_search_service,
                azure_extended_service=azure_extended_service,
                azure_full_search_service=azure_full_search_service,
                language_service=language_service,
                llm_service=llm_service,
                citation_service=citation_service,
                prompt_service=prompt_service,
            ),
        }

    def get(self, key: str) -> ChatApproach | None:
        """get gets the chat approach by key."""
        return self._registry.get(key)
