from __future__ import annotations

import base64
import re
from collections.abc import Callable
from io import BytesIO
from typing import overload

from dataloader.base import is_url
from pydantic import BaseModel
from pydantic import Field


__all__ = ["AccessModel", "DocumentInfo", "Document"]


class AccessModel(BaseModel):
    category: str = Field(..., alias="category")
    """The category of the document."""
    roles: list[str] = ["public"]
    """The roles that have access to the document.
    If roles not provided, the document is public."""


class DocumentInfo(AccessModel):
    name: str
    """The name of the document."""
    language: str | None = None
    """language is the primary language of the document."""

    def generate_document_id(self) -> str:
        """Generates a unique ID for the document."""
        id = base64.b16encode(self.name.encode("utf-8")).decode("ascii")
        if is_url(self.name):
            return f"url-{id}"
        return f"""file-{re.sub(r"[^a-zA-Z0-9]", "_", self.name)}-{id}"""


class Document(BaseModel):
    metadata: DocumentInfo = Field(..., alias="metadata")
    """The metadata of the document."""
    content: str | bytes | BytesIO = Field(..., alias="content")
    """The content of the document."""

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    @overload
    def get_content(self, typ: type[bytes]) -> bytes:
        """Get the content of the document as bytes."""
        ...

    @overload
    def get_content(self, typ: type[BytesIO]) -> BytesIO:
        """Get the content of the document as BytesIO."""
        ...

    @overload
    def get_content(self, typ: type[str]) -> str:
        """Get the content of the document as str."""
        ...

    def get_content(self, typ: type[bytes] | type[BytesIO] | type[str]) -> bytes | BytesIO | str:
        """Get the content of the document as the specified type."""

        def to_bytesIO() -> BytesIO:
            if isinstance(self.content, BytesIO):
                return self.content
            return BytesIO(to_bytes())

        def to_str() -> str:
            if isinstance(self.content, str):
                return self.content
            return to_bytes().decode()

        def to_bytes() -> bytes:
            if isinstance(self.content, bytes):
                return self.content
            if isinstance(self.content, str):
                return self.content.encode()
            if isinstance(self.content, BytesIO):
                return self.content.getvalue()
            if isinstance(self.content, bytearray):
                return bytes(self.content)
            if isinstance(self.content, memoryview):
                return self.content.tobytes()
            raise TypeError(f"Cannot convert {type(self.content)} to bytes")

        converters: dict[type, Callable[[], bytes | BytesIO | str]] = {
            bytes: to_bytes,
            BytesIO: to_bytesIO,
            str: to_str,
        }
        return converters[typ]()
