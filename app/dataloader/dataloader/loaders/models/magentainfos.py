from __future__ import annotations

from typing import Literal

from dataloader.loaders.models.base import BaseConfig
from pydantic import BaseModel
from pydantic import Field


class PublishDate(BaseModel):
    start: str = Field(..., alias="start")
    end: str = Field(..., alias="end")


DocumentType = Literal[
    "DTNews",
    "DTPhysicalProduct",
    "DTCampaign",
    "DTComplaints",
    "DTContact",
    "DTFAQ",
    "DTForm",
    "DTHR",
    "DTITSystemRelease",
    "DTManual",
    "DTOverviewPage",
    "DTProcess",
    "DTRollback",
    "DTSpeedDial",
    "DTTroubleshooting",
    "DTUniversal",
    "DTVirtualProduct",
    "DTBusinessCase",
]


class MagentaInfosConfig(BaseConfig):
    url: str = Field(..., alias="api_url")
    """The base URL of the Magenta Infos API."""
    auth_url: str = Field(..., alias="auth_url")
    """The URL to authenticate with the Magenta Infos API."""
    client_id: str = Field(..., alias="client_id")
    """The client ID to authenticate with the Magenta Infos API."""
    client_secret_ref: str = Field(..., alias="secret_reference")
    """The reference to the secret containing the client secret."""
    categories: list[str] = Field(..., alias="categories")
    """The list of categories to filter the documents by."""
    publish_date: PublishDate | None = Field(None, alias="publish_date")
    """The date range to filter the documents by."""
    rows: int | None = Field(None, alias="rows")
    """The number of rows to fetch from the API."""
    page: int | None = Field(None, alias="page")
    """The page number to fetch from the API."""
    type: DocumentType | None = Field(None, alias="type")
    """The type of document to filter by."""
