import os
from typing import Any
from typing import Dict
from typing import List

from .magenta_infos import DocumentRequest
from .magenta_infos import DocumentType
from .magenta_infos import MagentaInfosClient
from .magenta_infos import MIDocument
from .magenta_infos import PublishDate
from .staffbase import FormattedPost
from .staffbase import StaffbaseAPIClient


def get_staffbase_map(posts: List[FormattedPost], base: str) -> List[tuple[str, str, str]]:
    map: List[tuple[str, str, str]] = []

    for post in posts:
        content = post.get("content")
        text = f"{content.get('title')} : {content.get('content')}"
        source = post.get("url")

    map.append((source, base, text))
    return map


def custom_load_staffbase(
    url: str,
    api_key_reference: str,
    channels: List[str],
    posts: List[str],
    news_pages: List[str],
    publish_filter: str,
    language: str,
) -> List[FormattedPost]:

    api_key = os.getenv(api_key_reference)

    loader = StaffbaseAPIClient(url, api_key)
    all_posts = loader.get_posts(channels, posts, news_pages, publish_filter, language)
    return all_posts


def custom_load_magentainfos(
    auth_url: str,
    api_url: str,
    client_id: str,
    secret_reference: str,
    categories: List[str],
    document_list: List[DocumentRequest],
    publish_date: PublishDate | None,
    rows: int | None = None,
    page: int | None = None,
    type: DocumentType | None = None,
) -> List[Dict[str, Any]]:

    client_secret = os.getenv(secret_reference)
    if not client_secret:
        raise Exception("No client secret found")
    client = MagentaInfosClient(auth_url, api_url, client_id, client_secret, publish_date, rows, page, type)

    documents: List[Dict[str, Any]] = []

    if categories:
        document_pointers: List[MIDocument] = client.get_documents(categories)
        documents.extend(client.get_full_documents(document_pointers))

    for document_data in document_list:
        document = client.get_full_document(document_data)
        documents.append(document)

    return documents


def get_magentainfos_map(documents: List[Dict[str, Any]], base: str):
    map: List[tuple[str, str, str]] = []

    for doc in documents:

        content: str = ""

        if doc.get("title") and doc.get("description"):
            content = f"{doc.get('title')} : {doc.get('description')}"
        elif doc.get("title"):
            content = doc.get("title", "")
        elif doc.get("description"):
            content = doc.get("description", "")

        descriptions = doc.get("descriptions")

        if descriptions and isinstance(descriptions, list):
            for description in descriptions:
                if description.get("title") and description.get("description"):
                    content += f"\n{description.get('title')}: {description.get('description')}"
                elif description.get("description"):
                    content += f"\n{description.get('description')}"

        if content == "":
            continue

        text = content
        source = doc["url"]

        map.append((source, base, text))

    return map
