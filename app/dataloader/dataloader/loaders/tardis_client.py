from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import TypedDict

import requests


class AccessTokenResponse(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: str | None


class TardisClient:
    def __init__(
        self,
        auth_url: str,
        api_url: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self.auth_url = auth_url
        self.api_url = api_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = ""
        self.token_valid_until = datetime.now()
        self._get_access_token()

    def _get_access_token(self) -> None:
        """Get an access token from the oauth provider."""
        url: str = self.auth_url
        payload: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid",
        }
        response = requests.post(url, data=payload, timeout=30)
        if response.status_code != 200:
            raise Exception("Failed to fetch access token")
        token_info: AccessTokenResponse = response.json()
        self.access_token = token_info["access_token"]
        expires_in = token_info["expires_in"]
        self.token_valid_until = datetime.now() + timedelta(seconds=expires_in)

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a request to the API."""
        if not self.access_token or datetime.now() >= self.token_valid_until:
            self._get_access_token()

        headers: dict[str, str] = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs["headers"] = headers

        url = self.api_url

        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url_with_endpoint = f"{url}{endpoint}"

        response = requests.request(method, url_with_endpoint, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        return self._request("POST", endpoint, **kwargs)
