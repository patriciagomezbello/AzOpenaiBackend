from __future__ import annotations

from typing import Tuple
from urllib.parse import unquote
from urllib.parse import urlparse

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient


class SharePointUrlError(ValueError):
    """Raised when a SharePoint URL cannot be parsed."""


def get_graph_client(tenant_id: str, client_id: str, client_secret: str) -> GraphServiceClient:
    """Create authenticated GraphServiceClient using client credentials flow."""
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    return GraphServiceClient(credentials=credential)


def parse_sharepoint_url(sp_url: str) -> Tuple[str, str, str, str]:
    """Parse SharePoint URL into host, site_path, library_name, and folder.

    Args:
        sp_url: Full SharePoint URL (e.g., https://tenant.sharepoint.com/sites/MySite/Shared%20Documents/MyFolder)

    Returns:
        Tuple of (host, site_path, library_name, folder)

    Raises:
        SharePointUrlError: If URL format is invalid
    """
    parsed = urlparse(sp_url)
    if not parsed.scheme or not parsed.netloc:
        raise SharePointUrlError(f"Invalid SharePoint URL: {sp_url}")

    host = parsed.netloc
    path = parsed.path
    if path.startswith("/:") and "/r/" in path:
        path = path.split("/r/", 1)[1]
        if not path.startswith("/"):
            path = "/" + path

    parts = [p for p in path.strip("/").split("/") if p]
    if "sites" not in parts:
        raise SharePointUrlError("SharePoint URL must include /sites/{site}")

    sites_index = parts.index("sites")
    if len(parts) <= sites_index + 1:
        raise SharePointUrlError("SharePoint URL missing site name")

    site_path = "/".join(parts[: sites_index + 2])
    remaining = parts[sites_index + 2 :]
    if not remaining:
        raise SharePointUrlError("SharePoint URL missing library path")

    library_name = unquote(remaining[0])
    folder = unquote("/".join(remaining[1:]))
    return host, site_path, library_name, folder


def resolve_sharepoint_ids_from_url(
    sp_url: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    library_name: str | None = None,
) -> Tuple[str, str, str]:
    """Resolve SharePoint site_id, drive_id, and folder from URL using Microsoft Graph SDK.

    Args:
        sp_url: Full SharePoint URL
        tenant_id: Azure AD Tenant ID
        client_id: Azure AD App Client ID
        client_secret: Azure AD Client Secret
        library_name: Optional override for library name

    Returns:
        Tuple of (site_id, drive_id, folder)

    Raises:
        ValueError: If library not found or API calls fail
    """
    client = get_graph_client(tenant_id, client_id, client_secret)
    host, site_path, url_library, folder = parse_sharepoint_url(sp_url)
    selected_library = library_name or url_library

    # Get site ID using host and site path
    try:
        site_response = client.sites.get_by_path(path=site_path, drive_id=host)
        site_id = site_response.id
    except Exception as e:
        raise ValueError(f"Failed to resolve site from path '{site_path}': {e}") from e

    # Get drives and find matching library
    try:
        drives_response = client.sites.by_site_id(site_id).drives.get()
        drive_items = drives_response.value or []

        match = next(
            (d for d in drive_items if d.name and d.name.lower() == selected_library.lower()),
            None,
        )
        if not match:
            available = [d.name for d in drive_items if d.name]
            raise ValueError(f"Library '{selected_library}' not found. Available: {available}")

        return site_id, match.id, folder
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to resolve drives: {e}") from e
