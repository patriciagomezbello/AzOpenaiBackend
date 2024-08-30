from __future__ import annotations

from enum import Enum
from typing import Any

from dataloader.extractor.models import ExtractorConfig
from dataloader.indexer.models import SUPPORTED_LANGUAGES
from dataloader.indexer.models import SupportedLanguages
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer
from pydantic import SerializationInfo


class TextSplitter(Enum):
    DEFAULT = "standard"
    """Default splitter."""
    RECURSIVE = "recursive"
    """Recursive splitter."""
    DYNAMIC = "dynamic"
    """Dynamic splitter. Chose the best splitter based on the document content."""

    def __str__(self) -> str:
        return self.value


class ChunkerConfig(BaseModel):
    service: str = Field(..., alias="service")
    """The service name for the azure openai service that creates embeddings."""
    model: str = Field(..., alias="model")
    """The model to use for the embeddings."""
    timeout: float = Field(30.0, alias="timeout")
    """The timeout for the embedding creation."""
    splitter: TextSplitter = Field(TextSplitter.DEFAULT, alias="splitter")
    """The text splitter to use for the document."""

    @field_serializer("splitter", return_type=str)
    @classmethod
    def serialize_splitter(cls, v: Any, _: SerializationInfo) -> str:
        return str(v)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class IndexerConfig(BaseModel):
    """IndexerConfig contains the configuration for the indexer."""

    service: str
    """The service name for the search service."""
    index: str
    """The name of the search index."""
    chunker: ChunkerConfig
    """The configuration for the document chunker."""
    extractor: ExtractorConfig | None = None
    """The configuration for the default text extractor."""
    languages: tuple[SupportedLanguages, ...] = Field(default_factory=lambda: SUPPORTED_LANGUAGES)
    """The list of supported languages."""

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class DocumentChunk(BaseModel):
    """Represents a chunk extracted from a document."""

    id: str
    """The id of the chunk."""
    sourcepage: str
    """The source page of the chunk."""
    sourcefile: str
    """The source file of the chunk."""
    content: str
    """The text extracted from the chunk."""
    embedding: list[float]
    """The embedding of the chunk."""
    doclang: str | None
    """The language of the document."""
    category: str | None
    """The category of the document."""
    roles: list[str] | None
    """The roles that have access to the document."""
