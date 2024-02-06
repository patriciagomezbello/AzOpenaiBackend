from dataclasses import dataclass
from typing import List, Optional


@dataclass
class History:
    user: str
    bot: Optional[str]


@dataclass
class Overrides:
    retrieval_mode: str
    semantic_ranker: bool
    semantic_captions: bool
    top: int
    temperature: float


@dataclass
class ChatRequestData:
    history: List[History]
    approach: str = "rrr"
    overrides: Overrides = None


@dataclass
class DataPoint:
    docName: str
    page: int


@dataclass
class ChatResponseData:
    answer: str
    keywords: str
    data_points: List[DataPoint]


@dataclass
class ErrorMessage:
    code: int
    message: str


@dataclass
class ErrorResponseData:
    error: ErrorMessage


@dataclass
class CatResponse:
    categories: List[str]


@dataclass
class FeedbackRequestData:
    history: List[History]
    opinion: int


@dataclass
class FeedbackResponseData:
    response: str
