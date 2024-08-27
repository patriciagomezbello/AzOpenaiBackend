from __future__ import annotations

import base64
import os
from enum import Enum
from typing import overload
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from dataloader.indexer.models import AccessModel
from dataloader.indexer.models import Document
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders.models.langchain import ConfluenceConfig
from dataloader.loaders.models.langchain import DocusaurusConfig
from dataloader.loaders.models.langchain import GitConfig
from dataloader.loaders.models.langchain import WebsiteConfig
from dataloader.loaders.models.magentainfos import MagentaInfosConfig
from dataloader.loaders.models.staffbase import StaffbaseConfig
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document as LangchainDocument
from pydantic import Field

if TYPE_CHECKING:
    from dataloader.extractor.models import Page
    from dataloader.loaders.models.blob import File


class LoaderName(Enum):
    DOCUSAURUS = "docusaurus"
    """Docusaurus loader."""
    CONFLUENCE = "confluence"
    """Confluence loader."""
    WEBSITE = "rurl"
    """Website loader."""
    GIT = "git"
    """Git loader."""
    MAGENTAINFOS = "magentainfos"
    """Magenta Infos loader."""
    STAFFBASE = "staffbase"
    """Staffbase loader."""


_LANGCHAIN_LOADER_CONFIGS: dict[
    LoaderName,
    type[DocusaurusConfig | ConfluenceConfig | WebsiteConfig | GitConfig | MagentaInfosConfig | StaffbaseConfig],
] = {
    LoaderName.DOCUSAURUS: DocusaurusConfig,
    LoaderName.CONFLUENCE: ConfluenceConfig,
    LoaderName.WEBSITE: WebsiteConfig,
    LoaderName.GIT: GitConfig,
}


class LoaderConfig(AccessModel):
    name: LoaderName = Field(..., alias="name")
    """The name of the loader."""
    config: DocusaurusConfig | ConfluenceConfig | WebsiteConfig | GitConfig | MagentaInfosConfig = Field(..., alias="config")
    """The configuration of the loader."""

    def new_langchain_loader(self) -> BaseLoader:
        try:
            return self._ensure_config(_LANGCHAIN_LOADER_CONFIGS[self.name]).new_langchain_loader()
        except KeyError:
            raise ValueError(f"Loader {self.name=} is either not a langchain loader or not supported")

    @overload
    def _ensure_config(self, cls: type[DocusaurusConfig]) -> DocusaurusConfig: ...
    @overload
    def _ensure_config(self, cls: type[ConfluenceConfig]) -> ConfluenceConfig: ...
    @overload
    def _ensure_config(self, cls: type[WebsiteConfig]) -> WebsiteConfig: ...
    @overload
    def _ensure_config(self, cls: type[GitConfig]) -> GitConfig: ...
    @overload
    def _ensure_config(self, cls: type[MagentaInfosConfig]) -> MagentaInfosConfig: ...
    @overload
    def _ensure_config(self, cls: type[StaffbaseConfig]) -> StaffbaseConfig: ...

    def _ensure_config(
        self, cls: type[DocusaurusConfig | ConfluenceConfig | WebsiteConfig | GitConfig | MagentaInfosConfig | StaffbaseConfig]
    ) -> DocusaurusConfig | ConfluenceConfig | WebsiteConfig | GitConfig | MagentaInfosConfig | StaffbaseConfig:
        if not isinstance(self.config, cls):
            raise TypeError(f"Expected {cls.__name__} but got {type(self.config).__name__}")
        return self.config


class WebDocument(Document):
    @classmethod
    def from_langchain(cls, doc: LangchainDocument, cfg: LoaderConfig) -> WebDocument:
        # This is necessary as the base url can vary between different langchain loaders
        base_url = cfg.config.get_url()
        return cls(
            metadata=DocumentInfo(
                name=urljoin(base_url, str(doc.metadata["source"]).lstrip(base_url)),
                category=cfg.category,
                roles=cfg.roles,
            ),
            content=doc.page_content,
        )

    def to_file(self) -> File:
        from dataloader.loaders.models.blob import File

        name = base64.urlsafe_b64encode(self.metadata.name.encode()).decode()
        return File(
            metadata=DocumentInfo(
                name=self.metadata.name,
                category=self.metadata.category,
                roles=self.metadata.roles,
            ),
            content=self.content,
            path=os.path.join(self.metadata.category, f"{name}.html"),
        )

    def to_document(self):
        return Document(metadata=self.metadata, content=self.content)

    @classmethod
    async def to_pages(cls, doc: Document) -> list[Page]:
        """Extract pages from the document."""
        from dataloader.extractor.models import Page

        if isinstance(doc, WebDocument):
            return [Page.from_web_document(doc)]
        raise TypeError(f"Expected WebDocument, got {type(doc).__name__}")

    @classmethod
    def from_document(cls, doc: Document) -> WebDocument:
        return cls(metadata=doc.metadata, content=doc.content)
