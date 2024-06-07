from copy import deepcopy
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from typing import Optional

from api.models import Overrides
from azure.search.documents.aio import AsyncSearchItemPaged
from azure.search.documents.models import QueryCaptionResult
from azure.search.documents.models import QueryType
from azure.search.documents.models import VectorizedQuery
from clients import SearchClient
from config import SearchSettings
from lingua import Language
from services.language import LanguageService
from services.llm import LLMService
from services.logger import LOG_SENSITIVE_DATA
from services.logger import new_logger
from services.schemas import ChatCompletionsOptions
from services.schemas import ChatData
from services.schemas import ContextPrompt
from services.schemas import CreateEmbeddingOptions
from services.schemas import Document
from services.schemas import Facet
from services.schemas import LLMOptions
from services.schemas import Message
from services.schemas import SearchOptions
from services.search._interface import SearchService
from services.timer import timer
from services.utils import is_valid_url


logger = new_logger(__name__)


class AzureSearchService(SearchService):
    def __init__(
        self,
        cfg: SearchSettings,
        search_client: SearchClient,
        llm_svc: LLMService,
        lang_svc: LanguageService,
    ):
        self.cfg = cfg
        self.client = search_client
        self.llm_svc = llm_svc
        self.lang_service = lang_svc
        self.doclangs: List[Facet] = [{"value": "en", "count": 0}]

    @timer()
    async def build_query_prompt(self, msgs: List[Message], data: ChatData) -> str:
        """build_query_prompt builds a query prompt for the given messages and chat (meta)data.

        Raises:
            ValueError: If the query prompt cannot be built.

        Returns:
            str: The query prompt.
        """

        if len(msgs) == 0:
            logger.debug("Cannot build query prompt with no messages")
            raise ValueError("Cannot build query prompt with no messages")

        # We need to make a copy of the messages to avoid modifying the original list because lists are call by reference
        msgs = deepcopy(msgs)
        last_msg = msgs[-1]
        msgs[-1].set_content(f"Generate search query for: {msgs[-1].content()}")
        try:
            resp = await self.llm_svc.generate(
                msgs=msgs,
                options=LLMOptions(
                    chat=ChatCompletionsOptions(
                        temperature=0.0,
                        max_tokens=self.cfg.max_tokens,
                        n=1,
                    ),
                    context_prompt=ContextPrompt(template=self.cfg.system_prompt, data=data),
                ),
            )
        except Exception as e:
            logger.exception("Failed to generate query prompt", {"error": str(e)})
            raise ValueError("Failed to generate query prompt")

        if resp.strip() == "0":
            return last_msg.content()

        return resp

    @timer()
    async def cognitive_search(
        self, search_query: str, overrides: Overrides, lang: Language, roles: Optional[List[str]]
    ) -> List[Document]:
        """cognitive_search performs a search using the provided query and overrides.
        It returns the search results as a formatted string.
        """

        try:
            vector = await self.llm_svc.create_embedding(
                text=search_query,
                options=CreateEmbeddingOptions(),
            )

            docs = await self.client.search(
                SearchOptions(
                    search_text=search_query,
                    filter=self._build_filter(overrides, lang, roles),
                    query_type=QueryType.SEMANTIC,
                    semantic_configuration_name="default",
                    top=overrides.top,
                    query_caption=None,
                    vector_queries=[
                        VectorizedQuery(
                            fields="embedding",
                            vector=vector,
                        )
                    ],
                )
            )
        except Exception as e:
            logger.exception("Failed to search with query", {"query": search_query, "error": str(e)})
            raise ValueError(f"Failed to search with query '{search_query}': {e}")

        return await self._process_search_results(docs)

    def _build_filter(self, overrides: Overrides, lang: Language, roles: Optional[List[str]]) -> Optional[str]:
        """_build_filter builds a filter based on the provided overrides and language.
        Returns None if no filter is needed.
        """

        return self._combine_filters(
            self._build_lang_filter(overrides, lang),
            self._build_category_filter(overrides),
            self._build_role_filter(roles),
        )

    def _build_lang_filter(self, overrides: Overrides, lang: Language) -> Optional[str]:
        """_build_lang_filter builds a language filter based on the provided overrides and language.
        Returns None if no language filter is needed.
        """

        if overrides.multilingual_search:
            return None

        if self._empty_doclangs():
            return None

        facet_languages = self.lang_service.get_facet_languages(self.doclangs)
        if self.lang_service.get_lang_code(lang) not in facet_languages:
            return None

        return f"doclang eq '{self.lang_service.get_lang_code(lang)}'"

    def _build_category_filter(self, overrides: Overrides) -> Optional[str]:
        """_build_category_filter builds a category filter based on the provided overrides.
        Returns None if no category filter is needed.
        """

        if overrides.category_filter is None:
            return None

        if len(overrides.category_filter) == 0:
            return None

        filter = ""
        for cat in overrides.category_filter:
            filter += f"""category eq '{cat.replace("'", "''")}' or """

        return filter[:-4]

    def _build_role_filter(self, roles: Optional[List[str]]) -> str:
        """_build_role_filter builds a role filter based on the provided roles."""

        if not roles or len(roles) == 0:
            return "roles/any(r:search.in(r, 'public'))"

        return f"""roles/any(r:search.in(r, 'public, {", ".join(roles)}'))"""

    def _combine_filters(self, *filters: Optional[str]) -> str:
        """_combine_filters combines any number of filters into a single filter.

        The filters use the ODATA syntax. For example, to combine two filters, use:
        (filter1) and (filter2)

        For more information, see: https://learn.microsoft.com/en-us/azure/search/search-query-odata-filter
        """
        filter = ""
        for f in filters:
            if f is not None:
                filter += f"({f}) and "

        logger.debug("Combined filters", {"filter": filter[:-5]})
        return filter[:-5]

    async def _process_search_results(self, search_items: AsyncSearchItemPaged[Dict[str, Any]]) -> List[Document]:
        """_process_search_results processes the search results and returns a list of documents."""
        documents: List[Document] = []
        try:
            async for page in search_items.by_page():
                async for doc in page:
                    documents.append(
                        Document(
                            id=doc.get("id"),
                            content=doc.get("content"),
                            embedding=doc.get("embedding"),
                            image_embedding=doc.get("imageEmbedding"),
                            doclang=doc.get("doclang"),
                            category=doc.get("category"),
                            sourcepage=doc.get("sourcepage"),
                            roles=doc.get("roles"),
                            sourcefile=doc.get("sourcefile"),
                            captions=cast(List[QueryCaptionResult], doc.get("@search.captions")),
                            score=doc.get("@search.score"),
                            reranker_score=doc.get("@search.reranker_score"),
                        )
                    )
        except Exception as e:
            logger.exception("Failed to process search results", {"error": str(e)})
            raise ValueError(f"Failed to process search results: {e}")

        logger.debug(
            "Found search results",
            {"count": len(documents), "documents": ([doc.to_dict() for doc in documents] if LOG_SENSITIVE_DATA else "REDACTED")},
        )
        return documents

    def initialize_search_index(self, doclangs: List[Facet]) -> None:
        """initialize_search_index sets the local facets based on the provided facets."""
        self.doclangs = doclangs

    def _empty_doclangs(self) -> bool:
        """_empty_doclangs returns True if the doclangs facet is empty."""
        return self.doclangs is None or len(self.doclangs) == 0 or self.doclangs[0].get("count", 0) == 0


class AzureExtendedSearchService(AzureSearchService):
    """AzureExtendedSearchService extends AzureSearchService to provide additional search functionality.

    It searches not only for documents fitting the search query but also for document chunks around the search results."""

    def __init__(
        self,
        cfg: SearchSettings,
        search_client: SearchClient,
        llm_svc: LLMService,
        lang_svc: LanguageService,
    ):
        super().__init__(cfg, search_client, llm_svc, lang_svc)

    async def cognitive_search(
        self, search_query: str, overrides: Overrides, lang: Language, roles: Optional[List[str]]
    ) -> List[Document]:
        """cognitive_search performs a search using the provided query and overrides.
        It returns the search results as a formatted string.
        """

        documents: List[Document] = await super().cognitive_search(search_query, overrides, lang, roles)
        # TODO: Should we let the user decide when to use the extended search?
        if overrides.top > 3:
            return documents

        augmented: List[Document] = []
        for doc in documents:
            sourcepages = self._get_nearby_chunk_pages(doc.sourcepage)
            items = await self.client.get_documents(sourcepages)
            logger.debug("Found nearby chunk pages", {"sourcepages": sourcepages, "items": len(items)})
            augmented.extend(
                [doc]
                + [
                    Document(
                        id=item.get("id"),
                        content=item.get("content"),
                        embedding=item.get("embedding"),
                        image_embedding=item.get("imageEmbedding"),
                        doclang=item.get("doclang"),
                        category=item.get("category"),
                        sourcepage=item.get("sourcepage"),
                        roles=item.get("roles"),
                        sourcefile=item.get("sourcefile"),
                        captions=cast(List[QueryCaptionResult], item.get("@search.captions")),
                        score=item.get("@search.score"),
                        reranker_score=item.get("@search.reranker_score"),
                    )
                    for item in items
                ]
            )

        return augmented

    def _get_nearby_chunk_pages(self, sourcepage: Optional[str]) -> List[str]:
        """_get_nearby_chunk_pages returns the sourcepages of the chunks around the given sourcepage."""
        if not sourcepage:
            return []

        if is_valid_url(sourcepage):
            logger.debug("Skipping nearby chunk pages for URL", {"sourcepage": sourcepage})
            return []

        try:
            parts = sourcepage.split("-")
            doc_name = parts[:-1]
            chunk, suffix = parts[-1].split(".")
            chunk = int(chunk)
        except Exception as e:
            if isinstance(e, ValueError):
                logger.warning("Failed to parse chunk number", {"chunk": parts[-1].split(".")[0], "sourcepage": sourcepage})
                return []
            logger.exception("Failed to parse sourcepage", {"sourcepage": sourcepage})
            return []

        # TODO: Should we let the user decide how many nearby chunks to include? (range(-2, 3) gets the 4 chunks around the sourcepage) # noqa
        return [f"{'-'.join(doc_name)}-{chunk + i}.{suffix}" for i in range(-2, 3) if i != 0]
