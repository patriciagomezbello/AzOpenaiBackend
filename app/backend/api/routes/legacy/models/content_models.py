from dataclasses import dataclass
from typing import List
from typing import Optional


@dataclass
class indexedContent:
    """indexed Content response data."""

    count: int
    value: str


@dataclass
class ContentQueryString:
    """ContentQueryString represents the content query string data."""

    max_count: Optional[int]


@dataclass
class ContentResponse:
    """ContentResponse represents the content response data."""

    content: List[indexedContent]
