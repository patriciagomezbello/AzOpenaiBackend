from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import List
from typing import Optional


ChatMessageDict = dict[str, Optional[str]]


@dataclass
class ErrorMessage:
    """ErrorMessage represents an error message."""

    code: int
    message: str


@dataclass
class ErrorResponse:
    """ErrorResponse represents an error response."""

    error: ErrorMessage


@dataclass
class ChatMessage:
    """ChatMessage represents a chat message.
    A chat message always contains a user message and may contain a bot response
    to that message.
    It can also contain the model used to generate the bot response.
    """

    user: str
    bot: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> ChatMessageDict:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "user": self.user,
            "bot": self.bot,
            "model": self.model,
        }


@dataclass
class DataPoint:
    """DataPoint represents a citation data point."""

    docName: str
    page: Optional[int]


class SearchMode(Enum):
    """SearchMode represents the search mode for the search service."""

    DEFAULT = "default"
    EXTENDED = "extended"
    FULL = "full"


@dataclass
class Overrides:
    """Overrides represents overrides for the search query and AI request."""

    retrieval_mode: str = ""
    """retrieval_mode is the retrieval mode for the search query."""
    semantic_ranker: bool = False
    """semantic_ranker is whether to use the semantic ranker."""
    temperature: float = 0.7
    """The temperature to use for the final answer generation."""
    # TODO: Remove this field with v2 of the API, it is DEPRECATED.
    semantic_captions: bool = False
    """[DEPRECATED] Whether to use semantic captions for the search query.
    This field is deprecated and will be removed in v2 of the API."""
    top: int = 3
    """The number of k-top results to return from the search query.
    K-top results are the top k results from the search query that are used to generate the final answer.
    """
    category_filter: List[str] = field(default_factory=list)
    """category_filter is the category filter for the search query."""
    multilingual_search: bool = True
    """multilingual_search is whether to use multilingual search."""
    search_mode: SearchMode = SearchMode.DEFAULT
    """search_mode is the search mode for the search service."""
    search_span: Optional[int] = None
    """search_span is the search span for the search service.
    This is only used for the extended search mode.
    """

    def __post_init__(self):
        self.retrieval_mode = self.retrieval_mode or ""
        self.semantic_ranker = self.semantic_ranker or False
        self.temperature = self.temperature or 0.7
        self.semantic_captions = self.semantic_captions or False
        self.top = self.top or 3
        self.category_filter = self.category_filter or []
        self.multilingual_search = self.multilingual_search or True
        try:
            self.search_mode = SearchMode(self.search_mode) if isinstance(self.search_mode, str) else self.search_mode
        except ValueError:
            self.search_mode = SearchMode.DEFAULT
        self.search_span = self.search_span or None

    def fill_defaults(self, defaults: "Overrides") -> "Overrides":
        """fill_defaults can be used to fill in the missing values with the default values."""
        if self.retrieval_mode == "":
            self.retrieval_mode = defaults.retrieval_mode
        if self.semantic_ranker is False:
            self.semantic_ranker = defaults.semantic_ranker
        if self.semantic_captions is False:
            self.semantic_captions = defaults.semantic_captions
        if self.top == 0:
            self.top = defaults.top
        if self.temperature == 0.0:
            self.temperature = defaults.temperature
        return self

    def to_dict(self) -> dict[str, str | bool | float | List[str] | None]:
        """to_dict converts the dataclass to a dictionary."""
        return {
            "retrieval_mode": self.retrieval_mode,
            "semantic_ranker": self.semantic_ranker,
            "temperature": self.temperature,
            "semantic_captions": self.semantic_captions,
            "top": self.top,
            "category_filter": self.category_filter,
            "multilingual_search": self.multilingual_search,
            "search_mode": self.search_mode.value,
            "search_span": self.search_span,
        }
