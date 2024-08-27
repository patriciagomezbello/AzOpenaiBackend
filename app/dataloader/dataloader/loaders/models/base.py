from __future__ import annotations

from langchain_community.document_loaders.base import BaseLoader as LangchainBaseLoader
from pydantic import BaseModel


__all__ = ["BaseConfig"]


class BaseConfig(BaseModel):
    url: str
    """URL of the resource."""

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def new_langchain_loader(self) -> LangchainBaseLoader:
        """Creates a new langchain loader."""
        raise NotImplementedError(f"{self.__class__.__name__}.{self.new_langchain_loader.__name__}() not implemented")

    def get_url(self) -> str:
        """Get the url of the resource."""
        return self.url
