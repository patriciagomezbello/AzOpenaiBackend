from collections.abc import AsyncGenerator
from typing import Protocol

from chats import ChatRegistry
from clients._auth import OpenIDClient
from clients._openai import OpenAIClient
from clients._search import AzureSearchClient
from clients._storage import AzureStorageClient
from clients._table import AzureTableClient
from clients.factory import obtain_credential
from config import Config
from dependency_injector import containers
from dependency_injector import providers
from services.auth import OAuthService
from services.category import FacetCategoryService
from services.citation import RegexCitationService
from services.content import AzureBlobContentService
from services.feedback import FeedbackLogger
from services.language import LanguageProcessingService
from services.llm import OpenAIService
from services.logger import new_logger
from services.prompts import AzurePromptService
from services.search import AzureExtendedSearchService
from services.search import AzureFullSearchService
from services.search import AzureSearchService


logger = new_logger(__name__)


async def initialize_service(
    search_client: AzureSearchClient,
    azure_search_service: AzureSearchService,
    azure_extended_search_service: AzureExtendedSearchService,
    azure_full_search_service: AzureFullSearchService,
) -> AsyncGenerator[FacetCategoryService]:
    category_service = FacetCategoryService(search_client=search_client)
    await category_service.sync_facets(search_svc=azure_search_service)
    await category_service.sync_facets(search_svc=azure_extended_search_service)
    await category_service.sync_facets(search_svc=azure_full_search_service)
    logger.info("Synchronized facets with search service")
    yield category_service


class DIContainer(containers.DeclarativeContainer):
    _config = Config.load_config()

    settings = providers.Object(_config)
    settings_auth = providers.Object(_config.auth)
    settings_azure = providers.Object(_config.azure)
    settings_azure_openai = providers.Object(_config.azure.openai)
    settings_azure_search = providers.Object(_config.azure.search)
    settings_azure_storage = providers.Object(_config.azure.storage)
    settings_chat = providers.Object(_config.chat)
    settings_chat_abbreviations = providers.Object(_config.chat.abbreviations)
    settings_chat_settings = providers.Object(_config.chat.settings)
    settings_chat_settings_search = providers.Object(_config.chat.settings.search)
    settings_azure_table = providers.Object(_config.azure.table)

    credential = providers.Resource(obtain_credential)

    llm_client = providers.Resource(OpenAIClient, config=settings_azure_openai, credentials=credential)
    search_client = providers.Resource(AzureSearchClient, config=settings_azure_search, credentials=credential)
    storage_client = providers.Resource(AzureStorageClient, cfg=settings_azure_storage, credentials=credential)
    auth_client = providers.Singleton(OpenIDClient, cfg=settings_auth)
    table_client = providers.Resource(AzureTableClient, cfg=settings_azure_table, credentials=credential)

    regex_citation_service = providers.Singleton(RegexCitationService)
    azure_blob_content_service = providers.Singleton(AzureBlobContentService, client=storage_client)
    feedback_logger_service = providers.Singleton(FeedbackLogger)
    language_processing_service = providers.Singleton(LanguageProcessingService, abbreviations=settings_chat_abbreviations)
    openai_service = providers.Singleton(OpenAIService, client=llm_client)
    azure_table_service = providers.Singleton(AzurePromptService, client=table_client)

    azure_search_service = providers.Singleton(
        AzureSearchService,
        cfg=settings_chat_settings_search,
        search_client=search_client,
        llm_svc=openai_service,
        lang_svc=language_processing_service,
    )

    azure_extended_search_service = providers.Singleton(
        AzureExtendedSearchService,
        cfg=settings_chat_settings_search,
        search_client=search_client,
        llm_svc=openai_service,
        lang_svc=language_processing_service,
    )

    azure_full_search_service = providers.Singleton(
        AzureFullSearchService,
        cfg=settings_chat_settings_search,
        search_client=search_client,
        llm_svc=openai_service,
        lang_svc=language_processing_service,
    )

    facet_category_service = providers.Resource(
        initialize_service,
        search_client=search_client,
        azure_search_service=azure_search_service,
        azure_extended_search_service=azure_extended_search_service,
        azure_full_search_service=azure_full_search_service,
    )

    oauth_service = providers.Singleton(OAuthService, client=auth_client, cat_svc=facet_category_service)

    azure_prompt_service = providers.Singleton(AzurePromptService, client=table_client)

    chat_registry = providers.Factory(
        ChatRegistry,
        cfg=settings,
        azure_search_service=azure_search_service,
        azure_extended_service=azure_extended_search_service,
        azure_full_search_service=azure_full_search_service,
        language_service=language_processing_service,
        llm_service=openai_service,
        citation_service=regex_citation_service,
        prompt_service=azure_prompt_service,
    )


class Closable(Protocol):
    async def close(self) -> None: ...
