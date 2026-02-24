from __future__ import annotations

import fnmatch
import io
import os
import tempfile
from typing import Any
from urllib.parse import unquote

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient
from msgraph import GraphServiceClient

from ..document import get_document_text
from .sharepoint_utils import get_graph_client
from .sharepoint_utils import resolve_sharepoint_ids_from_url


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _split_patterns(pattern: str | None) -> list[str]:
    if not pattern:
        return []
    normalized = pattern.replace("|", ",")
    return _split_csv(normalized)


def _matches_file_pattern(file_name: str, pattern: str | None) -> bool:
    if not pattern:
        return True
    patterns = _split_patterns(pattern)
    if not patterns:
        return True
    return any(fnmatch.fnmatch(file_name, p) for p in patterns)


def _list_files(
    client: GraphServiceClient,
    site_id: str,
    drive_id: str,
    folder: str | None = None,
) -> list[dict[str, Any]]:
    """List files in a SharePoint folder using Graph SDK.

    Args:
        client: Authenticated GraphServiceClient
        site_id: SharePoint site ID
        drive_id: SharePoint drive ID
        folder: Optional folder path

    Returns:
        List of file/folder items
    """
    items: list[dict[str, Any]] = []

    try:
        if folder:
            normalized_folder = unquote(folder)
            request = client.sites.by_site_id(site_id).drives.by_drive_id(drive_id).root.item_with_path(normalized_folder).children
        else:
            request = client.sites.by_site_id(site_id).drives.by_drive_id(drive_id).root.children

        # Get all items, SDK handles pagination automatically
        response = request.get()
        items = [dict(item) for item in (response.value or [])]
    except Exception as e:
        raise ValueError(f"Failed to list files: {e}") from e

    return items


def _list_files_delta(
    client: GraphServiceClient,
    site_id: str,
    drive_id: str,
    folder: str | None = None,
) -> list[dict[str, Any]]:
    """List files using delta endpoint for tracking all items including hierarchies.

    Args:
        client: Authenticated GraphServiceClient
        site_id: SharePoint site ID
        drive_id: SharePoint drive ID
        folder: Optional folder path

    Returns:
        List of all file/folder items from delta
    """
    items: list[dict[str, Any]] = []

    try:
        if folder:
            normalized_folder = unquote(folder)
            request = client.sites.by_site_id(site_id).drives.by_drive_id(drive_id).root.item_with_path(normalized_folder).delta
        else:
            request = client.sites.by_site_id(site_id).drives.by_drive_id(drive_id).root.delta

        # Get all delta items, SDK handles pagination automatically
        response = request.get()
        items = [dict(item) for item in (response.value or [])]
    except Exception as e:
        raise ValueError(f"Failed to get delta items: {e}") from e

    return items


def _normalize_folder_path(folder: str | None) -> str:
    if not folder:
        return ""
    return "/".join(part for part in folder.split("/") if part)


def _is_ignored_path(path: str, ignore_folders: list[str]) -> bool:
    if not ignore_folders:
        return False
    parts = [p for p in path.split("/") if p]
    return any(part in ignore_folders for part in parts)


def _get_files(
    client: GraphServiceClient,
    site_id: str,
    drive_id: str,
    folder: str | None,
    recursive: bool,
    ignore_folders: list[str],
    file_pattern: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Get files from SharePoint with filtering and optional recursion.

    Args:
        client: Authenticated GraphServiceClient
        site_id: SharePoint site ID
        drive_id: SharePoint drive ID
        folder: Optional target folder path
        recursive: Whether to recursively search subdirectories
        ignore_folders: List of folder names to ignore
        file_pattern: Optional file pattern to match (supports multiple with |)

    Returns:
        List of (folder_path, item_dict) tuples
    """
    files: list[tuple[str, dict[str, Any]]] = []
    target_folder = _normalize_folder_path(folder)
    root_prefix = f"/drives/{drive_id}/root:"
    target_prefix = f"{root_prefix}/{target_folder}" if target_folder else root_prefix

    if not recursive:
        items = _list_files(client, site_id, drive_id, target_folder or None)
        current_path = target_folder
        for item in items:
            item_name = item.get("name", "")
            if item.get("file") and _matches_file_pattern(item_name, file_pattern):
                files.append((current_path, item))
        return files

    items = _list_files_delta(client, site_id, drive_id, target_folder or None)
    for item in items:
        if item.get("deleted") or not item.get("file"):
            continue
        item_name = item.get("name", "")
        if not _matches_file_pattern(item_name, file_pattern):
            continue

        parent_path = item.get("parentReference", {}).get("path", "")
        if target_prefix and parent_path and not parent_path.startswith(target_prefix):
            continue

        relative_dir = parent_path[len(target_prefix) :].lstrip("/") if parent_path else ""
        if _is_ignored_path(relative_dir, ignore_folders):
            continue

        current_path = f"{target_folder}/{relative_dir}" if target_folder else relative_dir
        current_path = current_path.strip("/")
        files.append((current_path, item))

    return files


def _download_file(client: GraphServiceClient, site_id: str, drive_id: str, item_id: str) -> bytes:
    """Download file content from SharePoint using Graph SDK.

    Args:
        client: Authenticated GraphServiceClient
        site_id: SharePoint site ID
        drive_id: SharePoint drive ID
        item_id: Item/file ID

    Returns:
        File content as bytes
    """
    try:
        response = client.sites.by_site_id(site_id).drives.by_drive_id(drive_id).items.by_drive_item_id(item_id).content.get()
        return response  # SDK returns bytes directly
    except Exception as e:
        raise ValueError(f"Failed to download file {item_id}: {e}") from e


def _build_blob_metadata_map(
    storageaccount: str | None,
    storage_creds,
    containerdocs: str | None,
) -> dict[str, dict[str, str]]:
    blob_metadata_map: dict[str, dict[str, str]] = {}
    if not storageaccount or not storage_creds or not containerdocs:
        return blob_metadata_map

    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(containerdocs)
    if blob_container.exists():
        for blob in blob_container.list_blobs(include=["metadata"]):
            if blob.name:
                blob_metadata_map[blob.name] = blob.metadata or {}
    else:
        blob_container.create_container()

    return blob_metadata_map


def _upload_blob_with_metadata(
    storageaccount: str | None,
    storage_creds,
    containerdocs: str | None,
    file_name: str,
    content: bytes,
    last_modified: str,
) -> None:
    if not storageaccount or not storage_creds or not containerdocs:
        return

    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(containerdocs)
    if not blob_container.exists():
        blob_container.create_container()

    blob_container.upload_blob(file_name, data=io.BytesIO(content), overwrite=True)

    blob_client = blob_container.get_blob_client(file_name)
    metadata = {"loader": "sharepoint", "sharepoint_modified_at": last_modified}
    blob_client.set_blob_metadata(metadata=metadata)


def _cleanup_orphaned_sharepoint_blobs(
    processed_files: set[str],
    storageaccount: str | None,
    storage_creds,
    containerdocs: str | None,
    search_creds,
    searchservice: str | None,
    index_name: str | None,
) -> None:
    if not storageaccount or not storage_creds or not containerdocs:
        return

    print("Cleaning up deleted SharePoint files...")

    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net",
        credential=storage_creds,
    )
    blob_container = blob_service.get_container_client(containerdocs)

    blobs_deleted: list[str] = []
    if blob_container.exists():
        for blob in blob_container.list_blobs(include=["metadata"]):
            blob_meta = blob.metadata or {}
            if blob_meta.get("loader") == "sharepoint" and blob.name:
                if blob.name not in processed_files:
                    print(f"  Deleting blob: {blob.name} (no longer in SharePoint)")
                    blob_container.delete_blob(blob.name)
                    blobs_deleted.append(blob.name)

    if blobs_deleted and search_creds and searchservice and index_name:
        from azure.search.documents import SearchClient

        search_client = SearchClient(
            endpoint=f"https://{searchservice}.search.windows.net/",
            index_name=index_name,
            credential=search_creds,
        )

        documents_to_delete = []
        for blob_name in blobs_deleted:
            results = search_client.search(
                search_text="*",
                filter=f"sourcefile eq '{blob_name}'",
                select=["id"],
            )
            for result in results:
                documents_to_delete.append({"id": result["id"]})

        if documents_to_delete:
            print(f"  Deleting {len(documents_to_delete)} index entries...")
            search_client.delete_documents(documents_to_delete)

    if blobs_deleted:
        print(f"  Cleanup complete ({len(blobs_deleted)} blobs deleted)")
    else:
        print("  No orphaned blobs found")


def _process_sharepoint_item(
    client: GraphServiceClient,
    site_id: str,
    drive_id: str,
    item: dict[str, Any],
    blob_metadata_map: dict[str, dict[str, str]],
    storageaccount: str | None,
    storage_creds,
    containerdocs: str | None,
    formrecognizer_creds,
    formrecognizerservice: str,
) -> tuple[list[tuple[str, str, str]], bool]:
    item_id = item.get("id")
    if not item_id:
        return [], False

    file_name = item.get("name", "")
    last_modified = item.get("lastModifiedDateTime", "")

    print(f"Processing file: {file_name}")

    if file_name in blob_metadata_map:
        stored_modified = blob_metadata_map[file_name].get("sharepoint_modified_at", "")
        if stored_modified == last_modified:
            print(f"  ✓ File unchanged (modified: {last_modified}), skipping")
            return [], True
        print(f"  ⟳ File changed (old: {stored_modified}, new: {last_modified}), re-indexing")
    else:
        print("  ✨ New file, indexing")

    content = _download_file(client, site_id, drive_id, item_id)
    print(f"  Downloaded {len(content)} bytes")

    _upload_blob_with_metadata(
        storageaccount,
        storage_creds,
        containerdocs,
        file_name,
        content,
        last_modified,
    )
    if storageaccount and storage_creds and containerdocs:
        print(f"  Uploaded to blob storage: {file_name}")

    page_map = _extract_text_from_bytes(content, file_name, formrecognizer_creds, formrecognizerservice)
    print(f"  Extracted {len(page_map)} pages")

    document_map: list[tuple[str, str, str]] = []
    if page_map:
        name_without_ext, ext = os.path.splitext(file_name)
        pages_added = 0

        for page_num, _, page_text in page_map:
            sanitized_text = page_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

            if sanitized_text.strip():
                if ext.lower() == ".pdf":
                    source_page = f"{name_without_ext}-{page_num}{ext}"
                else:
                    source_page = file_name

                document_map.append((source_page, file_name, sanitized_text))
                pages_added += 1

        print(f"  ✓ Added {pages_added} pages to document map")
    else:
        print("  ✗ No text extracted")

    return document_map, True


def _extract_text_from_bytes(
    content: bytes,
    filename: str,
    formrecognizer_creds,
    formrecognizerservice: str,
) -> list[tuple[int, int, str]]:
    """Extract text with page information.

    Returns:
        List of (page_num, offset, text) tuples
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    localpdf = ext == ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        page_map = get_document_text(
            file_path=tmp_path,
            formrecognizer_creds=formrecognizer_creds,
            formrecognizerservice=formrecognizerservice,
            localpdf=localpdf,
            verbose=False,
        )
        return page_map  # Return full page_map instead of concatenating
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def custom_load_sharepoint(
    config: dict[str, Any],
    formrecognizer_creds,
    formrecognizerservice: str,
    storageaccount: str | None = None,
    storage_creds=None,
    containerdocs: str | None = None,
    search_creds=None,
    searchservice: str | None = None,
    index_name: str | None = None,
) -> list[tuple[str, str, str]]:
    """Load documents from SharePoint using Microsoft Graph SDK.

    Args:
        config: Configuration dict with tenant_id, client_id, client_secret_ref, sharepoint_url, etc.
        formrecognizer_creds: Azure Form Recognizer credentials
        formrecognizerservice: Azure Form Recognizer service name
        storageaccount: Optional Azure Storage Account name
        storage_creds: Optional Azure Storage Account credentials
        containerdocs: Optional container name for blobs
        search_creds: Optional Azure Search credentials
        searchservice: Optional Azure Search service name
        index_name: Optional search index name

    Returns:
        List of (source_page, file_name, text) tuples
    """
    tenant_id = config.get("tenant_id")
    client_id = config.get("client_id")
    client_secret_ref = config.get("client_secret_ref", "")
    client_secret = os.getenv(client_secret_ref)

    if not tenant_id or not client_id or not client_secret:
        raise ValueError("SharePoint credentials missing (tenant_id/client_id/client_secret)")

    sharepoint_url = config.get("sharepoint_url")
    site_id = config.get("site_id")
    drive_id = config.get("drive_id")

    library_name = config.get("library_name")
    folder = config.get("folder")
    file_pattern = config.get("file_pattern")
    ignore_folders = config.get("ignore_folders") or []
    recursive = bool(config.get("recursive", True))

    if not site_id or not drive_id:
        if not sharepoint_url:
            raise ValueError("sharepoint_url is required when site_id/drive_id are missing")
        site_id, drive_id, inferred_folder = resolve_sharepoint_ids_from_url(
            sharepoint_url,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            library_name=library_name,
        )
        if not folder:
            folder = inferred_folder

    client = get_graph_client(tenant_id, client_id, client_secret)

    document_map: list[tuple[str, str, str]] = []
    indexed_sources: list[str] = []  # Track all sourcepages for cleanup
    files = _get_files(client, site_id, drive_id, folder, recursive, ignore_folders, file_pattern)

    print(f"Found {len(files)} files in SharePoint")

    # Build hashmap of existing blobs if storage is available
    blob_metadata_map = _build_blob_metadata_map(storageaccount, storage_creds, containerdocs)

    # Track which files were processed to detect deletions later
    processed_files: set[str] = set()

    for _, item in files:
        file_name = item.get("name", "")
        if file_name:
            processed_files.add(file_name)

        try:
            docs, should_index = _process_sharepoint_item(
                client,
                site_id,
                drive_id,
                item,
                blob_metadata_map,
                storageaccount,
                storage_creds,
                containerdocs,
                formrecognizer_creds,
                formrecognizerservice,
            )
            if docs:
                document_map.extend(docs)
                indexed_sources.extend([doc[0] for doc in docs])
            if not should_index:
                continue
        except (OSError, ValueError, RuntimeError, AzureError) as e:
            print(f"  ✗ Failed: {e}")
            continue

    print(f"Total document pages to index: {len(document_map)}")

    # Cleanup orphaned SharePoint files from blob storage and index
    try:
        _cleanup_orphaned_sharepoint_blobs(
            processed_files,
            storageaccount,
            storage_creds,
            containerdocs,
            search_creds,
            searchservice,
            index_name,
        )
    except (OSError, ValueError, RuntimeError, AzureError) as e:
        print(f"Error during cleanup: {e}")

    return document_map
