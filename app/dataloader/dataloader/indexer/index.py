import asyncio
import inspect
import os
from collections import Counter
from collections.abc import AsyncGenerator
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Generator
from collections.abc import Sequence
from typing import Any
from typing import Protocol
from urllib.parse import urlparse

from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import get_bearer_token_provider
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import _edm as FieldType
from azure.search.documents.indexes.models import SearchField
from azure.search.documents.indexes.models import SearchIndex
from dataloader.base import ClientManager
from dataloader.base import is_url
from dataloader.base import new_logger
from dataloader.extractor.models import Page
from dataloader.indexer.builder import IndexField
from dataloader.indexer.builder import new_index
from dataloader.indexer.language import LanguageDetector
from dataloader.indexer.models import ChunkerConfig
from dataloader.indexer.models import Document
from dataloader.indexer.models import DocumentChunk
from dataloader.indexer.models import DocumentInfo
from dataloader.indexer.models import IndexerConfig
from dataloader.indexer.models import TextSplitter
from dataloader.indexer.utils import aenumerate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AsyncAzureOpenAI


logger = new_logger(__name__)


class Indexer(ClientManager):
    def __init__(
        self,
        config: IndexerConfig,
        credential: ChainedTokenCredential,
        extractors: dict[type[Document], Callable[[Document], Coroutine[Any, Any, list[Page]]]] = {},
    ):
        super().__init__(credential)
        endpoint = f"https://{config.service}.search.windows.net"
        self.config = config
        self.language_detector = LanguageDetector(languages=config.languages)
        self.indexer = SearchIndexClient(
            endpoint=endpoint,
            index_name=config.index,
            credential=credential,
        )
        self.searcher = SearchClient(
            endpoint=endpoint,
            index_name=config.index,
            credential=credential,
        )
        self.chunker = DocumentChunker(config.chunker, credential)
        self.extractors: dict[type[Document], Callable[[Document], Coroutine[Any, Any, list[Page]]]] = extractors

    def set_extractor(self, typ: type[Document], extractor: Callable[[Document], Coroutine[Any, Any, list[Page]]]) -> None:
        """Set the extractor for the document type. Overrides any existing extractor for the type."""
        if not inspect.iscoroutinefunction(extractor):
            raise TypeError("Extractor must be a coroutine function that takes a Document and returns a list of Pages")
        self.extractors[typ] = extractor

    async def index_documents(self, documents: Sequence[Document], **kwargs: Any) -> list[Document]:
        """Index the documents in the search index. Returns a list of documents that failed to index.

        If the no extractor for the document type is found, a ValueError is raised.

        You can pass additional keyword arguments to adjust the indexing behavior.

        Keyword Arguments:
            index_name (str): The name of the index to use. If not provided, the default index is used.
            reset (bool): Whether to reset the index before indexing the documents.
            max_section_length(int): The maximum length of a section. Defaults to 1100.
            section_overlap(int): The overlap between sections. Defaults to 100.
            sentence_search_limit(int): The limit for searching for the end of a sentence. Defaults to 100.
        """  # noqa: E501
        index_name = str(kwargs.pop("index_name", self.config.index))
        if bool(kwargs.pop("reset", False)):
            await self.delete_index(index_name)
            logger.info(f"Index '{index_name}' was reset")
        await self.ensure_index(index_name)

        failed: list[Document] = []
        for document in documents:
            try:
                pages = await self.extractors[type(document)](document)
                doclang = Counter(self.language_detector.detect(page.text) for page in pages).most_common(1)[0][0]
                document.metadata.language = self.language_detector.get_lang_code(doclang)

                logger.info(
                    f"Extracted {len(pages)} pages for document {document.metadata.name}. "
                    f"Detected language: {doclang.name.capitalize()}"
                )
                await self._bulk_indexing(pages, document.metadata, **kwargs)
            except Exception as e:
                if isinstance(e, KeyError):
                    raise ValueError(
                        f"Unsupported document type '{type(document).__name__}', please provide an extractor for this type"
                    ) from e

                failed.append(document)
                logger.exception(f"Failed to index document {document.metadata.name}: {e}")
                continue
        return failed

    async def _bulk_indexing(self, pages: list[Page], metadata: DocumentInfo, **kwargs: Any) -> None:
        """Bulk index the pages in the search index."""
        BATCH_SIZE = 1000
        batch: list[DocumentChunk] = []
        async for i, chunk in aenumerate(self.chunker.chunk_document(pages, metadata, **kwargs)):
            batch.append(chunk)
            if i % BATCH_SIZE == 0:
                _ = await self.searcher.upload_documents([section.model_dump() for section in batch])
                batch.clear()

        if len(batch) > 0:
            _ = await self.searcher.upload_documents([section.model_dump() for section in batch])

    async def delete_document(self, document: DocumentInfo) -> None:
        try:
            while True:
                sourcefile = DocumentChunker.build_sourcefile(document.name)
                result = await self.searcher.search(
                    search_text="*",
                    filter=f"sourcefile eq '{sourcefile}'",
                    top=1000,
                    include_total_count=True,
                )
                if (await result.get_count()) == 0:
                    return

                ids = [{"id": r["id"]} async for r in result]
                _ = await self.searcher.delete_documents(ids)
                await asyncio.sleep(2)
        except Exception as e:
            raise ValueError(f"Failed to remove document {document.name}") from e

    async def ensure_index(self, name: str) -> None:
        index = new_index(name)
        if await self._is_deprecated(name):
            logger.warning(f"Index {name} is deprecated")
            index = self._add_deprecated_fields(index)
        _ = await self.indexer.create_or_update_index(index)

    async def delete_index(self, name: str) -> None:
        await self.indexer.delete_index(name)

    async def _is_deprecated(self, name: str) -> bool:
        try:
            index_fields = (await self.indexer.get_index(name)).fields
        except Exception:
            return False

        fields: dict[str, SearchField] = {field.name: field for field in index_fields}
        deprecated = False
        for n in ("accesskeys",):
            if fields.get(n) is not None:
                deprecated = True
                break
        return deprecated

    def _add_deprecated_fields(self, index: SearchIndex) -> SearchIndex:
        fields: list[SearchField] = index.fields
        fields.append(
            IndexField.Simple(
                name="accesskeys",
                type=FieldType.Collection(FieldType.String),
                filterable=True,
                retrievable=False,
                facetable=True,
                Nullable=True,
            )
        )
        return index


class Splitter(Protocol):
    def __call__(self, page: Page, /, **kwargs: Any) -> Generator[str, None, None]: ...


class DocumentChunker(ClientManager):
    API_VERSION = "2024-07-01-preview"
    """API_VERSION is the version of the OpenAI API to use."""

    def __init__(self, config: ChunkerConfig, credential: ChainedTokenCredential):
        super().__init__(credential)
        self.client = AsyncAzureOpenAI(
            api_version=self.API_VERSION,
            azure_endpoint=f"https://{config.service}.openai.azure.com",
            azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
        )
        self.config = config

    async def chunk_document(self, pages: list[Page], metadata: DocumentInfo, **kwargs: Any) -> AsyncGenerator[DocumentChunk, None]:
        """Chunk the document into sections.
        You can pass additional keyword arguments to adjust the chunking behavior.

        Args:
            pages (list[Page]): The pages to chunk.
            max_section_length (int): The maximum length of a section.
            section_overlap (int): The overlap between sections.
            sentence_search_limit (int): The limit for searching for the end of a sentence.
        """  # noqa: E501
        split = self.get_splitter()

        for page in pages:
            doc_id = metadata.generate_document_id()
            for i, section in enumerate(split(page, **kwargs)):
                embed = await self.client.embeddings.create(model=self.config.model, timeout=self.config.timeout, input=section)
                if not embed:
                    logger.warning(f"Failed to create embedding for section for page {page.document}, skipping chunk")
                    continue
                yield DocumentChunk(
                    id=self.generate_chunk_id(doc_id, page.document, i),
                    sourcefile=self.build_sourcefile(page.document),
                    sourcepage=self.build_sourcepage(page),
                    content=section,
                    embedding=embed.data[0].embedding,
                    doclang=metadata.language,
                    category=metadata.category,
                    roles=metadata.roles,
                )

    def get_splitter(self) -> Splitter:
        match self.config.splitter:
            case TextSplitter.DEFAULT:
                return self._split_text
            case TextSplitter.RECURSIVE:
                return self._split_text_recursive
            case _:
                raise ValueError(f"Unknown splitter {self.config.splitter=}")

    # TODO: refactor this method to be more readable and simpler
    def _split_text(self, page: Page, /, **kwargs: Any) -> Generator[str, None, None]:  # noqa
        """Split the text into sections."""
        SENTENCE_ENDINGS = [".", "!", "?"]
        WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
        max_section_length = int(kwargs.pop("max_section_length", 1100))
        section_overlap = int(kwargs.pop("section_overlap", 100))
        sentence_search_limit = int(kwargs.pop("sentence_search_limit", 100))
        logger.debug(f"""Splitting {page.document}{"-page-" + str(page.number) if page.number else ""} into sections""")

        all_text = page.text
        length = len(all_text)
        start = 0
        end = length
        while start + section_overlap < length:
            last_word = -1
            end = start + max_section_length

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while (
                    end < length
                    and (end - start - max_section_length) < sentence_search_limit
                    and all_text[end] not in SENTENCE_ENDINGS
                ):
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word  # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while (
                start > 0
                and start > end - max_section_length - 2 * sentence_search_limit
                and all_text[start] not in SENTENCE_ENDINGS
            ):
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield section_text

            last_table_start = section_text.rfind("<table")
            if last_table_start > 2 * sentence_search_limit and last_table_start > section_text.rfind("</table"):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside sentence_search_limit, we ignore it,
                # as that will cause an infinite loop for tables longer than max_section_length
                # If last table starts inside section_overlap, keep overlapping
                start = min(end - section_overlap, start + last_table_start)
            else:
                start = end - section_overlap

        if start + section_overlap < end:
            yield all_text[start:end]

    def _split_text_recursive(self, page: Page, /, **kwargs: Any) -> Generator[str, None, None]:
        """Split the text into sections recursively."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=kwargs.get("max_section_length", 1100),
            chunk_overlap=kwargs.get("section_overlap", 100),
        )

        for section in splitter.split_text(page.text):
            yield section

    @staticmethod
    def generate_chunk_id(doc_id: str, name: str, number: int) -> str:
        """Generates a unique ID for the document chunk."""
        if is_url(name):
            return f"{doc_id}-{number}"
        # Unfortunatly, the naming of this id is inconsistent, but we need to keep it for backwards compatibility.
        # We're creating a chunk id here so if this were to be refactored, we would need to change the scheme to be:
        # <doc_id>-chunk-<number>
        return f"{doc_id}-page-{number}"

    @staticmethod
    def build_sourcefile(document_name: str) -> str:
        if is_url(document_name):
            url = urlparse(document_name)
            return f"{url.scheme}://{url.netloc}"
        return os.path.basename(document_name)

    @staticmethod
    def build_sourcepage(page: Page) -> str:
        if is_url(page.document):
            return page.document

        name, extension = page.document.rsplit(".", 1)
        if extension.lower() != "pdf":
            return os.path.basename(page.document)
        number = f"-{page.number}" if page.number is not None else ""
        return f"{name}{number}.{extension}"
