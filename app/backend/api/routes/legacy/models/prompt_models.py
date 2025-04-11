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
class PromptModificationResponse:
    """PromptModificationResponse represents the response data of the prompt creating/updating/deleting function."""

    response: str


@dataclass
class PromptRequest:
    """PromptRequest represents the prompt request data."""

    prompt: str
    name: str


@dataclass
class UpdatePromptRequest:
    """PromptRequest represents the prompt request data."""

    key: str
    prompt: str
    name: str


@dataclass
class DeletePromptRequest:
    """DeletePromptRequest represents the prompt request data."""

    key: str
