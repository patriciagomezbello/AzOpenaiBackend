from dataclasses import dataclass


@dataclass
class Prompt:
    """Prompt represents the prompt data stored in the azure storage table."""

    key: str
    name: str
    prompt: str


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

    prompt: str
    name: str
