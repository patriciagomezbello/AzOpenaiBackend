from dataclasses import dataclass
from io import BytesIO
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TypeAlias
from typing import Union

from azure.search.documents.models import QueryCaptionResult
from azure.search.documents.models import QueryCaptionType
from azure.search.documents.models import QueryType
from azure.search.documents.models import VectorQuery
from lingua import Language
from openai._types import NOT_GIVEN
from openai._types import NotGiven
from openai.types.chat import ChatCompletionMessageParam


__all__ = [
    "ChatCompletionsOptions",
    "CreateEmbeddingOptions",
    "SearchOptions",
    "ChatData",
    "ContextPrompt",
    "LLMOptions",
    "Model",
    "Message",
    "FileWrapper",
    "Facet",
    "Facets",
    "Document",
]

FacetValue: TypeAlias = Union[str, int]
Facet: TypeAlias = Dict[str, FacetValue]
Facets: TypeAlias = Dict[str, List[Facet]]


@dataclass
class ChatCompletionsOptions:
    """ChatCompletionsOptions represents the options for the chat completions API.
    It is utilized for generating a response in a chat conversation based on the provided options.

    This may only be used with the OpenAI API.
    """

    # Add additional options as needed
    messages: Optional[List[ChatCompletionMessageParam]] = None
    model: Optional[str] = None
    temperature: Union[float, NotGiven, None] = NOT_GIVEN
    max_tokens: Union[int, NotGiven, None] = NOT_GIVEN
    n: Union[int, NotGiven, None] = NOT_GIVEN
    top_p: Union[float, NotGiven, None] = NOT_GIVEN
    frequency_penalty: Union[float, NotGiven, None] = NOT_GIVEN
    presence_penalty: Union[float, NotGiven, None] = NOT_GIVEN
    stop: Union[str, List[str], NotGiven, None] = NOT_GIVEN


@dataclass
class CreateEmbeddingOptions:
    """CreateEmbeddingOptions represents the options for the create embedding API.
    It is utilized for creating an embedding vector representing the input text.

    This may only be used with the OpenAI API.
    """

    # Add additional options as needed
    model: Optional[str] = None
    input: Optional[Union[str, List[str], List[int], List[List[int]]]] = None
    timeout: Union[float, None, NotGiven] = NOT_GIVEN


@dataclass
class SearchOptions:
    """SearchOptions represents the options for the search API.
    It is utilized for searching an index based on the provided options.

    This may only be used with the Azure Search Service API.
    """

    # Add additional options as needed
    search_text: Optional[str] = None
    filter: Optional[str] = None
    query_type: Optional[Union[str, QueryType]] = None
    semantic_configuration_name: Optional[str] = None
    top: Optional[int] = None
    query_caption: Optional[Union[str, QueryCaptionType]] = None
    vector_queries: Optional[List[VectorQuery]] = None
    skip: Optional[int] = None
    select: Optional[List[str]] = None
    search_fields: Optional[List[str]] = None
    facets: Optional[List[str]] = None
    order_by: Optional[List[str]] = None
    include_total_count: Optional[bool] = None


@dataclass
class ChatData:
    """ChatData holds the data of the chat conversation."""

    language: Language
    no_idea_message: str
    injected_instructions: Optional[str]

    def to_dict(self) -> dict[str, str]:
        lang = self.language.name.lower().capitalize()
        # TODO: Simplify this in the future (probably with v2?), we can't do it now since it'd be a breaking change
        # Additionally we should then unify template variable names to be either camelCase or snake_case.
        return {
            "language": lang,
            "promptlang": lang,
            "noidea": self.no_idea_message,
            "injected_prompt": (self.injected_instructions if self.injected_instructions else ""),
        }


@dataclass
class ContextPrompt:
    """ContextPrompt represents a context prompt for generating a response with context."""

    template: str
    data: ChatData


def _remove_new_lines(text: str) -> str:
    """_remove_new_lines removes new lines from the text and replace them with spaces."""
    return text.replace("\n", " ").replace("\r", " ")


@dataclass
class Document:
    """Document represents a document in the search index."""

    id: Optional[str]
    """id represents the document id."""
    content: Optional[str]
    """content contains the document content."""
    embedding: Optional[List[float]]
    """embedding is the document embedding vector."""
    image_embedding: Optional[List[float]]
    """image_embedding is the document image embedding vector."""
    doclang: Optional[str]
    """doclang is the primary language of the document.
    For example: "en"
    """
    category: Optional[str]
    """category is the category of the document.
    For example: "Azure"
    """
    roles: Optional[List[str]]
    """roles are the roles that have access to the document.
    For example: ["manager", "employee"] or ["public"]
    """
    sourcepage: Optional[str]
    """sourcepage is the name of the document with its page number.
    For example: "data-3.pdf" -> document name = "data", page number = 3
    """
    sourcefile: Optional[str]
    """sourcefile is the name of the document file.
    For example: "data.pdf"
    """
    captions: List[QueryCaptionResult]
    """captions are the semantic search captions.
    For more information on this, please refer to the Azure AI Search documentation.
    """
    score: Optional[float] = None
    """score represents the match score in relation to the search query."""
    reranker_score: Optional[float] = None
    """reranker_score represents the match score after the reranker."""

    def __str__(self) -> str:
        """__str__ returns the document content as a string."""
        if self.content is None:
            return f"{self.sourcepage}: No content available"

        if self.sourcepage is None:
            return _remove_new_lines(self.content)

        return f"{self.sourcepage}: {_remove_new_lines(self.content)}"

    EmbeddingType = Optional[List[str]]
    CaptionsType = List[dict[str, Any]]

    def to_dict(
        self,
    ) -> dict[str, Union[str, float, EmbeddingType, CaptionsType, None]]:
        """to_dict returns the document as a dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "embedding": Document._trim_embedding(self.embedding),
            "imageEmbedding": Document._trim_embedding(self.image_embedding),
            "doclang": self.doclang,
            "category": self.category,
            "roles": self.roles,
            "sourcepage": self.sourcepage,
            "sourcefile": self.sourcefile,
            "captions": (
                [
                    {
                        "additional_properties": caption.additional_properties,
                        "text": caption.text,
                        "highlights": caption.highlights,
                    }
                    for caption in self.captions
                ]
                if self.captions
                else []
            ),
            "score": self.score,
            "reranker_score": self.reranker_score,
        }

    @classmethod
    def _trim_embedding(cls, embedding: Optional[List[float]]) -> Optional[str]:
        """_trim_embedding returns a trimmed list of floats from the embedding vector."""

        if embedding is None:
            return None

        if len(embedding) > 2:
            return f"[{embedding[0]}, {embedding[1]} ...+{len(embedding) - 2} more]"

        return str(embedding)


@dataclass
class LLMOptions:
    """LLMOptions represents options for generating a response with the LLM Service."""

    chat: ChatCompletionsOptions
    context_prompt: Optional[ContextPrompt] = None
    enhanced_context: Optional[List[Document]] = None


class Model:
    """Model represents a language model.
    It has several utility methods for handling model names and token limits.
    """

    ANSWER_TOKEN_LIMIT = 1024

    # _TOKEN_MAPPING maps model names to token limits.
    _TOKEN_MAPPING: dict[str, int] = {
        # TODO: Starting with model version 1106 and 0125, the token limit for "gpt-35-turbo" is 16385.
        "gpt-35-turbo": 4096,
        "gpt-35-turbo-16k": 16384,
        "gpt-35-turbo-instruct": 4096,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-5": 400000,
        "gpt-5-mini": 400000,
        "gpt-5-nano": 400000,
        "o1": 200000,
        "o3": 200000,
        "o3-mini": 200000,
        "o4-mini": 200000,
    }

    # _AZURE_OPENAI lists all the supported OpenAI model names for Azure.
    _AZURE_OPENAI: list[str] = [
        "gpt-35-turbo",
        "gpt-35-turbo-16k",
        "gpt-35-turbo-instruct",
        "gpt-4",
        "gpt-4-32k",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "o1",
        "o3",
        "o3-mini",
        "o4-mini",
    ]

    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        """__str__ returns the string representation of the model."""
        return self.value

    def is_valid(self) -> bool:
        """is_valid returns whether the model name is valid."""
        return self.value in self._AZURE_OPENAI

    def token_limit(self) -> int:
        """token_limit returns the token limit for the model."""
        return self._TOKEN_MAPPING[self.value]

    def parse(self) -> str:
        """parse returns the associated openai model string for the given model.

        Raises:
            ValueError: If the model is not recognized/supported.
        """

        if self.is_valid():
            return self.value

        raise ValueError(f"model {self} is not supported")


class Message:
    """Message represents a message in the chat."""

    # SYSTEM_ROLE represents the system role in the chat.
    SYSTEM_ROLE = "system"
    # ASSISTANT_ROLE represents the assistant role in the chat.
    ASSISTANT_ROLE = "assistant"
    # USER_ROLE represents the user role in the chat.
    USER_ROLE = "user"

    def __init__(self, value: dict[str, str]):
        self._value = value

    def role(self) -> str:
        """role returns the message author's role."""
        return self._value["role"]

    def content(self) -> str:
        """content returns the content of the message."""
        return self._value["content"]

    def set_content(self, content: str):
        """set_content sets the content of the message."""
        self._value["content"] = content

    def is_system(self) -> bool:
        """is_system returns whether the message author is "system"."""
        return self.role() == self.SYSTEM_ROLE

    def is_assistant(self) -> bool:
        """is_assistant returns whether the message author is "assistant"."""
        return self.role() == self.ASSISTANT_ROLE

    def is_user(self) -> bool:
        """is_user returns whether the message author is "user"."""
        return self.role() == self.USER_ROLE

    def to_chat_request_message(self) -> ChatCompletionMessageParam:
        """to_chat_request_message returns the message as a ChatCompletionMessageParam."""
        if self.is_system():
            return {"role": self.SYSTEM_ROLE, "content": self.content()}
        if self.is_assistant():
            return {"role": self.ASSISTANT_ROLE, "content": self.content()}
        return {"role": self.USER_ROLE, "content": self.content()}


class FileWrapper:
    """File is a class that holds the file data."""

    def __init__(self, name: str, mimetype: str, data: BytesIO):
        self.name = name
        self.mimetype = mimetype
        self.data = data


class SavedPrompt:
    """SavedPrompt represents a saved prompt."""

    def __init__(
        self,
        key: str,
        name: str,
        prompt: str,
    ):
        self.key = key
        self.name = name
        self.prompt = prompt

    def __to_dict__(self) -> dict:
        """__to_dict__ returns the dict representation of the saved prompt."""
        return {"key": self.key, "name": self.name, "prompt": self.prompt}


class NewPrompt:
    """NewPrompt is a model for creating new prompts."""

    name: str
    prompt: str

    def __init__(
        self,
        name: str,
        prompt: str,
    ):
        self.name = name
        self.prompt = prompt

    def to_dict(self) -> dict:
        """to_dict converts the dataclass to a dictionary."""
        return {"name": self.name, "prompt": self.prompt}

    def is_valid(self) -> bool:
        """is_valid returns whether the new prompt is valid."""
        if not self.name or not self.prompt:
            return False
        return True


class UpdatePrompt:
    """UpdatePrompt is a model for updateing an existing prompt."""

    key: str
    name: str
    prompt: str

    def __init__(
        self,
        key: str,
        name: str,
        prompt: str,
    ):
        self.key = key
        self.name = name
        self.prompt = prompt

    def to_dict(self) -> dict:
        """to_dict converts the dataclass to a dictionary."""
        return {"key": self.key, "name": self.name, "prompt": self.prompt}

    def is_valid(self) -> bool:
        """is_valid returns whether the new prompt is valid."""
        if not self.name or not self.prompt or not self.key:
            return False
        return True


class DeletePrompt:
    """DeletePrompt is a model for deleting an existing prompt."""

    key: str

    def __init__(self, key: str):
        self.key = key

    def to_dict(self) -> dict:
        """to_dict converts the dataclass to a dictionary."""
        return {"key": self.key}

    def is_valid(self) -> bool:
        """is_valid returns whether the prompt is valid."""
        if not self.key:
            return False
        return True
