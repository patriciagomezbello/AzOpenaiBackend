from dataclasses import dataclass


@dataclass
class Prompt:
    """Prompt represents the prompt data stored in the azure storage table."""

    PartitionKey: str
    RowKey: str
    Prompt: str
    PromptName: str


@dataclass
class PromptResponse:
    """PromptResponse represents the prompt response data."""

    prompts: list[Prompt]


@dataclass
class PromptCreationResponse:
    """PromptCreationResponse represents the prompt creation response data."""

    response: str


@dataclass
class PromptRequest:
    """PromptRequest represents the prompt request data."""

    Prompt: str
    PromptName: str
