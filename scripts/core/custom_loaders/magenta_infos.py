import time
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import TypedDict
from urllib.parse import urlparse

from requests import HTTPError

from .tardis_client import TardisClient


class PublishDate(TypedDict):
    start: str
    end: str


class MetaInfo(TypedDict):
    total: int
    requestId: str
    status: str


class PagingInfo(TypedDict):
    currentPage: int
    pageCount: int
    rows: int


class MIDocument(TypedDict):
    id: str
    locale: str
    type: str
    title: str
    publishDate: str
    version: str


class ApiResponse(TypedDict):
    meta: MetaInfo
    paging: PagingInfo
    documents: List[MIDocument]


class Category(TypedDict):
    id: str
    type: str
    level: int
    name: str
    children: List[str]


class DocumentRequest:
    id: str
    type: str
    teaser: Optional[bool] = False


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


class MagentaInfosClient:
    def __init__(
        self,
        auth_url: str,
        api_url: str,
        client_id: str,
        client_secret: str,
        publish_date: PublishDate | None = None,
        rows: int | None = None,
        page: int | None = None,
        type: DocumentType | None = None,
    ) -> None:
        self.api_client = TardisClient(auth_url, api_url, client_id, client_secret)
        self.api_url = api_url
        self.publish_date = publish_date
        self.rows = rows
        self.page = page
        self.type: DocumentType | None = type

    def get_document_list(
        self,
        category: str,
        page: int | None = None,
        rows: int | None = None,
        type: DocumentType | None = None,
    ) -> List[MIDocument]:
        document_list: List[MIDocument] = []
        current_page = page if page else 1
        total_pages = 1

        data: Dict[str, Any] = {"categoryId": category}

        if type:
            data["type"] = type
        if self.publish_date:
            data["publishDate"] = {
                "from": self.publish_date["start"],
                "to": self.publish_date["end"],
            }
        if rows:
            data["rows"] = rows

        while current_page <= total_pages:
            if page:
                data["page"] = current_page
            response: ApiResponse = self.api_client.post("/documents", json=data).json()
            documents = response.get("documents", [])
            if not documents:
                break
            document_list.extend(documents)

            current_page = response.get("paging").get("currentPage") + 1
            total_pages = response.get("paging").get("pageCount")

        return document_list

    # Whoever wants to type this, feel free, I am not doing this.
    # https://developer.telekom.de/catalog/wins/wins-export-api/g_api/playground/1.1.0#/components/schemas/DocumentResponse
    def get_full_document(self, data: DocumentRequest) -> Dict[str, Any]:
        response = self.api_client.post("/document", json=data)
        document: Dict[str, Any] = response.json()
        document["url"] = self._build_url(document["id"], document["type"])
        return document

    def get_documents(self, categories: List[str]) -> List[MIDocument]:
        all_documents: List[MIDocument] = []
        for category in categories:
            documents = self.get_document_list(category, self.page, self.rows, self.type)
            all_documents.extend(documents)
        return all_documents

    def get_full_documents(self, document_list: List[MIDocument]) -> List[Dict[str, Any]]:

        # see comment on get_documents function
        documents: List[Any] = []

        for document in document_list:
            data = {"id": document["id"], "type": document["type"]}
            try:
                response = self.api_client.post("/document", json=data).json()
            except HTTPError as e:
                if e.response.status_code != 404:
                    print(e)
                    break
                print(f"Document with id {document['id']} not found")
                continue

            full_document: Dict[str, Any] = response.json()
            full_document["url"] = self._build_url(full_document["id"], full_document["type"])
            documents.append(full_document)
            time.sleep(2)

        return documents

    def _build_url(self, document_id: str, document_type: str) -> str:

        parsed_url = urlparse(self.api_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        return f"{base_url}/{document_type}/{document_id}"
