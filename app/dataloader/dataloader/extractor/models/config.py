from __future__ import annotations

from pydantic import BaseModel


class ExtractorConfig(BaseModel):
    """Configuration for the text extractor."""

    service: str
    """The service name for the OCR service."""
