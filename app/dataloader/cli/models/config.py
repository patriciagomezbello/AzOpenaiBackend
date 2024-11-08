from __future__ import annotations

import json
import os
from typing import Any
from typing import TypeVar

from cli.core.parser import ParsedArgs
from dataloader.indexer.models import AccessModel
from dataloader.indexer.models import IndexerConfig
from dataloader.indexer.models import TextSplitter
from dataloader.loaders.models import ConfluenceConfig
from dataloader.loaders.models import DocusaurusConfig
from dataloader.loaders.models import GitConfig
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import LoaderName
from dataloader.loaders.models import WebsiteConfig
from lingua import Language
from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class CategoryRBACMap(BaseModel):
    access: list[AccessModel] = Field(..., alias="access")

    @classmethod
    def load(cls, config: dict[str, list[str]]) -> CategoryRBACMap:
        return cls(access=[AccessModel(category=cat, roles=roles) for cat, roles in config.items()])

    def get_roles(self, category: str) -> list[str]:
        if category in ("public", ""):
            return ["public"]

        for cat in self.access:
            if cat.category == category:
                return cat.roles
        return ["public"]


class WebLoaderConfig(BaseModel):
    name: LoaderName = Field(..., alias="loader")
    """The name of the loader."""
    category: str = Field("", alias="category")
    """Which category the resulting documents should be in."""
    config: DocusaurusConfig | ConfluenceConfig | WebsiteConfig | GitConfig = Field(..., alias="config")
    """The configuration of the loader."""
    splitter: str = Field("", alias="splitter", deprecated=True)
    """The splitter for the loader.
    This is deprecated and will be removed in the future.
    It does not have any effect on the loader."""

    def to_loader_config(self, role_config: CategoryRBACMap) -> LoaderConfig:
        return LoaderConfig(
            name=self.name,
            config=self.config,
            category=self.category,
            roles=role_config.get_roles(self.category),
        )


class CLIConfig(BaseModel):
    role_config: CategoryRBACMap
    """The role configuration for the CLI."""
    loader_config: list[LoaderConfig]
    """The loader configuration for the CLI."""
    indexer_config: IndexerConfig
    """The indexer configuration for the CLI."""
    data_mode: str = Field("all", alias="data_mode")
    """The mode for the data."""
    file_mode: str = Field("file", alias="file_mode")
    """The mode for the files."""
    reset_index: bool = Field(False, alias="reset_index")
    """Whether to reset the index."""
    storage_account: str = Field(..., alias="storage_account")
    """The storage account to use."""
    data_container: str = Field(..., alias="containerdata")
    """The name of the blob container where manually uploaded data is stored."""
    docs_container: str = Field(..., alias="containerdocs")
    """The name of the blob container where the documents are stored."""
    local_files: str = Field("data", alias="files")
    """The path to the local files."""
    max_section_length: int = Field(1100, alias="max_section_length")
    """The maximum length of a section in the search index."""

    @classmethod
    def load(cls, args: ParsedArgs) -> CLIConfig:
        """Loads the configuration from the config files."""
        webloader_data = cls.read_config(args.webloader_config, list[dict[str, Any]])
        indexer_data = cls.read_config(args.indexer_config, dict[str, Any])
        role_data = cls.read_config(args.roles_config, dict[str, Any])

        return cls.load_from_data(webloader_data, indexer_data, role_data)

    @classmethod
    def read_config(cls, file: str, typ: type[T], *, fail_silently: bool = True) -> T:
        try:
            with open(file, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            if fail_silently:
                return typ()
            raise FileNotFoundError(f"Config file {file} not found.")
        except Exception as e:
            raise OSError(f"Failed to load config from {file}") from e
        return data

    @classmethod
    def load_from_data(cls, lc_data: list[dict[str, Any]], indexer_data: dict[str, Any], role_data: dict[str, Any]) -> CLIConfig:
        storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
        if not storage_account:
            raise ValueError("No storage account provided.")

        role_config = cls.load_roles_config(role_data)
        return cls(
            role_config=role_config,
            loader_config=[cls.load_webloader_config(loader, role_config) for loader in lc_data],
            indexer_config=cls.load_indexer_config(indexer_data),
            data_mode=os.getenv("DATA_MODE", "file"),
            file_mode=os.getenv("FILE_MODE", "blob"),
            reset_index=os.getenv("RESET_INDEX", "false").lower() in ["true", "1"],
            storage_account=storage_account,
            containerdata=os.getenv("AZURE_STORAGE_CONTAINER_DATA", "data"),
            containerdocs=os.getenv("AZURE_STORAGE_CONTAINER_DOCS", "docs"),
            files=os.getenv("LOCAL_FILES", "data"),
            max_section_length=int(os.getenv("MAX_SECTION_LENGTH", "1100")),
        )

    @classmethod
    def load_indexer_config(cls, config: dict[str, Any]) -> IndexerConfig:
        """Loads the configuration from the given dictionary."""
        if "languages" in config and len(config["languages"]) > 0 and isinstance(config["languages"][0], str):
            config["languages"] = [Language[str(lang).upper()] for lang in config["languages"]]

        search_service = os.getenv("AZURE_SEARCH_SERVICE")
        if not search_service:
            raise ValueError("No search service provided.")
        config["service"] = search_service

        index = os.getenv("AZURE_SEARCH_INDEX")
        if not index:
            raise ValueError("No search index provided.")
        config["index"] = index

        formrecognizer_service = os.getenv("AZURE_FORMRECOGNIZER_SERVICE")
        if not formrecognizer_service:
            raise ValueError("No ocr service provided.")
        if "extractor" not in config:
            config["extractor"] = {}
        config["extractor"]["service"] = formrecognizer_service

        openai_service = os.getenv("AZURE_OPENAI_SERVICE")
        if not openai_service:
            raise ValueError("No openai service provided.")
        if "chunker" not in config:
            config["chunker"] = {}
        config["chunker"]["service"] = openai_service

        openai_deployment = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
        if not openai_deployment:
            raise ValueError("No openai deployment provided.")
        config["chunker"]["model"] = openai_deployment
        config["chunker"]["timeout"] = float(os.getenv("AZURE_OPENAI_TIMEOUT", "60"))
        config["chunker"]["splitter"] = os.getenv("TEXT_SPLITTER", TextSplitter.DEFAULT.value)

        return IndexerConfig.model_validate(config)

    @classmethod
    def load_webloader_config(cls, config: dict[str, Any], role_config: CategoryRBACMap) -> LoaderConfig:
        return WebLoaderConfig.model_validate(config).to_loader_config(role_config)

    @classmethod
    def load_roles_config(cls, config: dict[str, Any]) -> CategoryRBACMap:
        return CategoryRBACMap.load(config)
