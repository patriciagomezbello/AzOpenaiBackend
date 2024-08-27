from __future__ import annotations

from dataloader.loaders.models import WebDocument
from pydantic import BaseModel


class Page(BaseModel):
    """Represents a page extracted from a document."""

    document: str
    """The name of the document the page was extracted from."""
    text: str
    """The text extracted from the page."""
    number: int | None
    """The page number. If the document is not paginated, this will be None."""
    offset: int | None
    """The offset of the page in the document. If the document is not paginated, this will be None."""

    def __str__(self) -> str:
        return self.text

    @classmethod
    def from_web_document(cls, doc: WebDocument) -> Page:
        """Create a Page from a WebDocument."""
        return cls(
            document=doc.metadata.name,
            text=doc.get_content(str),
            number=None,
            offset=None,
        )
