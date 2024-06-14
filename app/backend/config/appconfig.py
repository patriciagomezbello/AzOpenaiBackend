import importlib
import json
import os
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import List
from typing import Optional
from urllib.parse import ParseResult
from urllib.parse import urlparse

from services.logger import new_logger
from services.schemas import Model


def _safe_import(module: str, name: str) -> Optional[Any]:
    """_safe_import imports the module and returns the attribute with the given name.
    Returns None if the module or attribute does not exist."""
    try:
        mod = importlib.import_module(module)
        return getattr(mod, name)
    except ImportError:
        return None
    except AttributeError:
        return None


abbreviations: Optional[dict[str, str]] = _safe_import("core.abbrev", "abbreviations")
query_prompt_template: Optional[str] = _safe_import("core.context", "query_prompt_template")
system_message_chat_conversation: Optional[str] = _safe_import("core.context", "system_message_chat_conversation")

logger = new_logger(__name__)


class InvalidConfigError(Exception):
    """InvalidConfigError is an error that is raised when the configuration is invalid."""

    pass


@dataclass
class GPTConfig:
    """GPTConfig is a class that holds the configuration for the GPT model."""

    deployment: str = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "")
    model: Model = field(default_factory=lambda: Model(os.getenv("AZURE_OPENAI_CHATGPT_MODEL", "")))
    embed_deployment: str = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "")

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.deployment == "":
            raise InvalidConfigError("AZURE_OPENAI_CHATGPT_DEPLOYMENT is required")
        try:
            _ = self.model.parse()
        except ValueError as e:
            raise InvalidConfigError(f"AZURE_OPENAI_CHATGPT_MODEL is invalid: {str(e)}")
        if self.embed_deployment == "":
            raise InvalidConfigError("AZURE_OPENAI_EMB_DEPLOYMENT is required")


@dataclass
class OpenAIConfig:
    """OpenAIConfig is a class that holds the configuration for the OpenAI services."""

    service: str = os.getenv("AZURE_OPENAI_SERVICE", "")
    gpt: GPTConfig = field(default_factory=GPTConfig)

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.service == "":
            raise InvalidConfigError("AZURE_OPENAI_SERVICE is required")
        self.gpt.validate()


@dataclass
class SearchConfig:
    """SearchConfig is a class that holds the configuration for the Azure Search service."""

    service: str = os.getenv("AZURE_SEARCH_SERVICE", "")
    index: str = os.getenv("AZURE_SEARCH_INDEX", "")

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.service == "":
            raise InvalidConfigError("AZURE_SEARCH_SERVICE is required")
        if self.index == "":
            raise InvalidConfigError("AZURE_SEARCH_INDEX is required")


@dataclass
class StorageConfig:
    """StorageConfig is a class that holds the configuration for the Azure Storage service."""

    account: str = os.getenv("AZURE_STORAGE_ACCOUNT", "")
    container: str = os.getenv("AZURE_STORAGE_CONTAINER_DOCS", "")

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.account == "":
            raise InvalidConfigError("AZURE_STORAGE_ACCOUNT is required")
        if self.container == "":
            raise InvalidConfigError("AZURE_STORAGE_CONTAINER_DOCS is required")


@dataclass
class AzureConfig:
    """AzureConfig is a class that holds the configuration for the Azure services."""

    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)

    def validate(self) -> None:
        """validate validates the configuration."""
        self.openai.validate()
        self.search.validate()
        self.storage.validate()


@dataclass
class SearchSettings:
    """SearchSettings is a class that holds the configuration for the search service."""

    system_prompt: str = os.getenv("QUERY_SYSTEM_PROMPT", query_prompt_template or "")
    max_tokens: int = int(os.getenv("MAX_TOKENS_QUERY", 32))

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.system_prompt == "":
            raise InvalidConfigError("QUERY_SYSTEM_PROMPT is required")
        if self.max_tokens <= 0:
            raise InvalidConfigError("MAX_TOKENS_QUERY must be greater than 0")


@dataclass
class AnswerSettings:
    """AnswerSettings is a class that holds the configuration for the answer service."""

    system_prompt: str = os.getenv("ANSWER_SYSTEM_PROMPT", system_message_chat_conversation or "")
    max_tokens: int = int(os.getenv("MAX_TOKENS_ANSWER", 1024))

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.system_prompt == "":
            raise InvalidConfigError("ANSWER_SYSTEM_PROMPT is required")
        if self.max_tokens <= 0:
            raise InvalidConfigError("MAX_TOKENS_ANSWER must be greater than 0")


@dataclass
class ChatSettings:
    """ChatSettings is a class that holds the configuration for the chat service."""

    # TODO: To set the system prompts per environment variables using azd, we'd need a solution to a bug of azd
    # that fails to read multi-line strings from environment variables.
    search: SearchSettings = field(default_factory=SearchSettings)
    answer: AnswerSettings = field(default_factory=AnswerSettings)

    def validate(self) -> None:
        """validate validates the configuration."""
        self.search.validate()
        self.answer.validate()


@dataclass
class ChatConfig:
    """ChatConfig is a class that holds the configuration for the chat service."""

    # TODO: Since azd env get-values escapes the double quotes, we'd need to write a custom json parser that
    # handles the escaped double quotes since json doesn't support single quotes.
    abbreviations: dict[str, str] = field(
        default_factory=lambda: json.loads(os.getenv("ABBREVIATIONS", json.dumps(abbreviations or {})))
    )
    settings: ChatSettings = field(default_factory=ChatSettings)

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.abbreviations == {}:
            logger.warning("No abbreviations found")
        self.settings.validate()


@dataclass
class ManagedIdentityConfig:
    """ManagedIdentityConfig is a class that holds the configuration for the managed identity service."""

    client_id: str = os.getenv("AZURE_AUTH_CLIENT", "")
    tenant: str = os.getenv("AZURE_AUTH_TENANT", "same")


@dataclass
class ICUConfig:
    """ICUConfig is a class that holds the configuration for the ICU identity provider."""

    client_id: str = os.getenv("AZURE_AUTH_ICU_CLIENT", "")
    url: str = os.getenv("AZURE_AUTH_ICU_ISSUER_URL", "")


@dataclass
class AuthConfig:
    """AuthConfig is a class that holds the configuration for the authentication service."""

    allowed_roles: Optional[List[str]] = field(default_factory=lambda: AuthConfig._parse_roles())
    azure: ManagedIdentityConfig = field(default_factory=ManagedIdentityConfig)
    icu: ICUConfig = field(default_factory=ICUConfig)

    @staticmethod
    def _parse_roles() -> Optional[List[str]]:
        roles = os.getenv("AZURE_AUTH_ROLE", "all")
        return None if roles == "all" else [role.strip() for role in roles.split(",")]

    def validate(self) -> None:
        """validate validates the configuration."""
        if self.allowed_roles == "":
            raise InvalidConfigError("AZURE_AUTH_ROLE is required")


class Config:
    """Config is a class that holds the configuration for the backend."""

    def __init__(self):
        self.api_path: str = os.getenv("API_BASE_PATH", "/")
        self.azure = AzureConfig()
        self.chat = ChatConfig()
        self.auth = AuthConfig()

    def validate(self) -> None:
        """validate validates the configuration."""
        if os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG":
            logger.warning("Running in debug mode")

        parsed: ParseResult = urlparse(self.api_path)
        if not parsed.path or not self.api_path.startswith("/"):
            raise InvalidConfigError("API_BASE_PATH must be a valid path")
        self.azure.validate()
        self.chat.validate()
        self.auth.validate()

    @staticmethod
    def load_config() -> "Config":
        """load_config loads the configuration from the environment."""
        cfg = Config()
        logger.info("Loaded configuration")
        cfg.validate()
        return cfg
