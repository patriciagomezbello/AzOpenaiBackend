import os
from collections.abc import Generator
from typing import Any
from urllib.parse import urljoin
from urllib.parse import urlparse

from dataloader.base import new_logger
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders.base import WebDocumentLoader
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import MagentaInfosConfig
from dataloader.loaders.models import WebDocument
from dataloader.loaders.tardis_client import TardisClient
from requests import HTTPError


logger = new_logger(__name__)


class MagentaInfosLoader(WebDocumentLoader):
    def __init__(self, config: LoaderConfig):
        self.loader_config = config
        self.config = config._ensure_config(MagentaInfosConfig)

        client_secret = os.getenv(self.config.client_secret_ref)
        if not client_secret:
            raise ValueError("Client secret not found")

        self.client = TardisClient(self.config.auth_url, self.config.url, self.config.client_id, client_secret)

    def lazy_load(self) -> Generator[WebDocument, None, None]:
        documents = self._get_documents(self.config.categories)
        for doc in documents:
            full_doc = self._get_full_document({"id": doc["id"], "type": doc["type"]})
            yield self._convert_to_web_document(full_doc)

    def _get_documents(self, categories: list[str]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for category in categories:
            documents.extend(self._get_document_list(category, self.config.page, self.config.rows, self.config.type))
        return documents

    def _get_document_list(
        self,
        category: str,
        page: int | None = None,
        rows: int | None = None,
        type: str | None = None,
    ) -> list[dict[str, Any]]:
        documents: list[Any] = []
        current_page = page if page else 1
        total_pages = 1

        data: dict[str, Any] = {"categoryId": category}
        if type:
            data["type"] = type
        if self.config.publish_date:
            data["publishDate"] = {
                "from": self.config.publish_date.start,
                "to": self.config.publish_date.end,
            }
        if rows:
            data["rows"] = rows

        while current_page <= total_pages:
            if page:
                data["page"] = current_page
            response: dict[str, Any] = self.client.post("/documents", json=data).json()
            documents = response.get("documents", [])
            if not documents:
                break
            documents.extend(documents)

            pagination: dict[str, Any] = response.get("paging", {})
            current_page = pagination.get("currentPage")
            if not current_page:
                break
            current_page += 1

            total_pages = pagination.get("pageCount")
            if not total_pages:
                break

        return documents

    # TODO: Type this correctly
    # https://developer.telekom.de/catalog/wins/wins-export-api/g_api/playground/1.1.0#/components/schemas/DocumentResponse
    def _get_full_document(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            document: dict[str, Any] = self.client.post("/document", json=data).json()
            document["url"] = self._build_url(document["id"], document["type"])
            return document
        except HTTPError as e:
            if e.response.status_code != 404:
                logger.exception("Failed to fetch document", extra={"error": e})
                return {}

            logger.error(f"Document with id {data['id']} not found")
            return {}

    def _build_url(self, document_id: str, document_type: str) -> str:
        url = urlparse(self.config.url)
        base_url = f"{url.scheme}://{url.netloc}"
        return urljoin(base_url, f"{document_type}/{document_id}")

    def _convert_to_web_document(self, document: dict[str, Any]) -> WebDocument:
        title = document.get("title", "")
        if title != "":
            title = f"{title} : "

        description = document.get("description", "")
        content = f"{title}{description}"

        descriptions: list[dict[str, Any]] = document.get("descriptions", [])
        for description in descriptions:
            title = description.get("title", "")
            if title != "":
                title = f"{title}: "
            content += f"\n{title}{description.get('description')}"

        return WebDocument(
            metadata=DocumentInfo(
                name=document["url"],
                category=self.loader_config.category,
                roles=self.loader_config.roles,
            ),
            content=content,
        )
