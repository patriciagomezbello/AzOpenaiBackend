from __future__ import annotations

import logging
import os
from collections.abc import Callable
from urllib.parse import urljoin
from urllib.parse import urlsplit

from bs4 import BeautifulSoup as Soup
from dataloader.loaders.models.base import BaseConfig
from langchain_community.document_loaders import ConfluenceLoader
from langchain_community.document_loaders import DocusaurusLoader
from langchain_community.document_loaders import GitLoader
from langchain_community.document_loaders import RecursiveUrlLoader
from pydantic import Field


class DocusaurusConfig(BaseConfig):
    def new_langchain_loader(self) -> DocusaurusLoader:
        """Create a new DocusaurusLoader."""
        return DocusaurusLoader(url=self.url)


class ConfluenceConfig(BaseConfig):
    username: str
    """The username of the user."""
    token_ref: str
    """Name of variable where API key of user is put."""
    space_key: str
    """Space from wiki/confluence."""
    include_attachments: bool = Field(False, alias="include_att")
    """Whether to include attachments."""
    limit: int = Field(10, alias="limit")
    """Limit of items."""
    max_pages: int = Field(10, alias="max_pages")
    """Maximum number of pages for pagination."""

    def get_url(self) -> str:
        """Get the url of the confluence view."""
        url = urlsplit(self.url)
        if "/display/" in url.path:
            return self.url
        return urljoin(self.url, f"/display/{self.space_key}")

    def new_langchain_loader(self) -> ConfluenceLoader:
        """Create a new Confluence loader."""
        include_att = self.include_attachments
        if include_att is None or include_att:
            # Including attachments will take a very long time
            # TODO: Implement a way to include attachments
            # As an option we could use the lazy_load iterator to
            # load only a certain amount of attachments
            include_att = False

        # TODO: This is a little bit tricky, as the cli should definitely use the token_ref
        # but an implementing microservice may not want to set the token for every request
        # TODO: We should discuss how to handle this
        token = os.getenv(self.token_ref)
        if not token:
            logging.warning("No token found in 'token_ref' environment variable. Defaulting to the token_ref value.")
            token = self.token_ref

        # Confluence has two ways to authenticate, either with a username and an api token
        # or with only a token. To catch both cases, we need to check if the username is set
        username = None
        if self.username and self.username.lower() != "token":
            username = self.username

        return ConfluenceLoader(
            url=self.url,
            username=username,
            token=token if not username else None,
            api_key=token if username else None,
            space_key=self.space_key,
            include_attachments=include_att,
            limit=self.limit,
            max_pages=self.max_pages,
        )


class WebsiteConfig(BaseConfig):
    max_depth: int | None = Field(3, alias="max_depth")
    """Maximum depth for crawling."""

    def new_langchain_loader(self) -> RecursiveUrlLoader:
        """Create a new RecursiveUrlLoader."""
        return RecursiveUrlLoader(
            url=self.url,
            max_depth=self.max_depth,
            extractor=lambda x: Soup(x, "html.parser").text,
        )


class GitConfig(BaseConfig):
    repo_path: str
    """Path of the git repository.
    For example if your (base) url is github.com then the path is ./path/to/repo."""
    branch: str
    """Which branch of the repository to use."""
    filter: Callable[[str], bool] = Field(lambda _: True, exclude=True)
    """Filter function to filter out files."""

    def new_langchain_loader(self) -> GitLoader:
        """Create a new GitLoader."""
        return GitLoader(
            clone_url=self.url,
            repo_path=self.repo_path if self.repo_path else "./",
            branch=self.branch,
            file_filter=self.filter,
        )
