from typing import Literal
from typing import TypedDict

from dataloader.loaders.models.base import BaseConfig
from pydantic import Field


class Content(TypedDict):
    content: str
    image: dict
    teaser: str
    title: str


class Post(TypedDict):
    contents: dict[str, Content]
    id: str | None
    externalID: str | None
    channelID: str | None
    campaignId: str | None
    planned: str | None
    published: str | None
    created: str | None
    updated: str | None


class ChannelApiResponse(TypedDict):
    total: int
    limit: int
    offset: int
    data: list[Post]


class Pagination(TypedDict):
    href: str
    method: str


class NewsApiResponse(TypedDict):
    links: dict[Literal["next"], Pagination]
    data: list[Post]


class FormattedPost(TypedDict):
    content: Content
    url: str
    id: str | None
    externalID: str | None
    channelID: str | None
    campaignId: str | None
    planned: str | None
    published: str | None
    created: str | None
    updated: str | None


class StaffbaseConfig(BaseConfig):
    api_key_ref: str = Field(..., alias="api_key_reference")
    """The reference to the secret containing the API key."""
    channels: list[str] = Field(..., alias="channels")
    """The list of channels to fetch posts from."""
    news_pages: list[str] = Field(..., alias="news_pages")
    """The list of news pages to fetch content from."""
    posts: list[str] = Field(..., alias="posts")
    """The list of posts to fetch."""
    publish_filter: str = Field(..., alias="publish_filter")
    """Filter specifying which posts to publish."""
    language: Literal["de", "en"] = Field(..., alias="language")
    """The language to fetch the content in."""
