import json
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional

import jwt
import requests
from cachetools import TTLCache
from config import AuthConfig
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from services.logger import new_logger


logger = new_logger(__name__)

Token = Dict[str, Any]


__all__ = [
    "AuthClient",
    "Token",
    "AllowedRoles",
    "AuthenticatedToken",
    "InvalidTokenError",
    "UnknownProviderError",
]


@dataclass
class AllowedRoles:

    key: str
    roles: Optional[list[str]]


@dataclass
class AuthenticatedToken:
    """DecodedToken is a data class that represents a decoded JWT token along with additional information."""

    # token is the decoded token
    token: Token
    # allowed_roles are the roles that are allowed to access
    allowed_roles: AllowedRoles


class InvalidTokenError(Exception):
    """InvalidTokenError is an exception that is raised when a token is invalid."""


class UnknownProviderError(Exception):
    """UnknownProviderError is an exception that is raised when the token provider is not recognized."""


class AuthClient(ABC):
    """AuthClient is an abstract class that defines the methods that must be implemented by any authentication client."""

    @abstractmethod
    def decode_token(self, token: str) -> AuthenticatedToken: ...


@dataclass
class ProviderSpec:
    """ProviderSpec is a data class that represents the specification of an OpenID provider."""

    # The URL of the OpenID provider
    url: str
    # The client ID of the OpenID provider
    client_id: str
    # allowed_roles are the roles that are allowed to access the service
    # It is mapped to the OIDC field that contains the roles claim
    # This may differ depending on the provider
    # If all roles are allowed, the value is None
    allowed_roles: AllowedRoles
    # issuer is the OpenID provider issuer URL
    # This may differ from the URL depending on the provider
    issuer: str
    # verify_token is a callback function that verifies the token
    # If not provided, the token is verified by the audience, issuer and public key
    verify_token: Optional[Callable[[str, bytes], Token]]
    # same_tenant is a flag that indicates if the tenant is the same as the client
    # This may only be relevant for Azure Managed Identity
    same_tenant: bool = False


class TokenProvider(ABC):
    """TokenProvider is an abstract class that defines the methods that must be implemented by any token provider."""

    @abstractmethod
    def matches_issuer(self, issuer: str) -> bool: ...

    @abstractmethod
    def get_spec(self) -> ProviderSpec: ...


class Provider(Enum):
    """Provider is an enumeration that represents the different token providers.
    The token provider is used to identify the type of token and decode it accordingly.
    """

    AZURE = "azure"
    ICU = "icu"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def len() -> int:
        return len(Provider.__members__)


class OpenIDClient(AuthClient):
    def __init__(self, cfg: AuthConfig):
        self.providers: dict[Provider, TokenProvider] = {
            Provider.AZURE: Azure(cfg.azure.tenant, cfg.azure.client_id, cfg.allowed_roles),
            Provider.ICU: ICU(cfg.icu.url, cfg.icu.client_id, cfg.allowed_roles),
        }
        self.cache: TTLCache[str, Token] = TTLCache(maxsize=Provider.len(), ttl=3600)
        self.mutex = Lock()

    def decode_token(self, token: str) -> AuthenticatedToken:
        """decode_token decodes a JWT token and returns the decoded token if the token is valid.

        Raises:
            ErrInvalidToken: If the token is invalid
            ErrInvalidTokenType: If the token provider is not recognized
            Exception: If an error occurs while decoding the token

        Returns:
            DecodedToken: The decoded token if the token is valid
        """
        try:
            provider = self.providers[self._identify_provider(token)]
            spec = provider.get_spec()
            if spec.same_tenant:
                return AuthenticatedToken(
                    token=jwt.decode(
                        jwt=token,
                        algorithms=["RS256"],
                        options={"verify_signature": False},
                    ),
                    allowed_roles=spec.allowed_roles,
                )

            return self._decode_and_verify_jwt(token=token, spec=spec, retry=True)

        except Exception as e:
            if isinstance(e, UnknownProviderError) or isinstance(e, InvalidTokenError):
                raise
            raise Exception(f"Error while decoding token: {e.args[0]}")

    def _identify_provider(self, token: str) -> Provider:
        """_identify_provider identifies the token provider based on the issuer URL."""

        tk: Token = jwt.decode(jwt=token, algorithms=["RS256"], options={"verify_signature": False})
        issuer = self._get_issuer(tk)
        for p in Provider:
            if self.providers[p].matches_issuer(issuer):
                return p
        raise UnknownProviderError("Invalid token type")

    def _decode_and_verify_jwt(self, token: str, spec: ProviderSpec, retry: bool) -> AuthenticatedToken:
        """_decode_and_verify_jwt decodes and verifies a JWT token using the OpenID keys."""

        try:
            public_key = self._get_public_key(token, self._get_openid_keys(spec.url))
            if spec.verify_token:
                return AuthenticatedToken(
                    token=spec.verify_token(token, public_key),
                    allowed_roles=spec.allowed_roles,
                )

            return AuthenticatedToken(
                token=jwt.decode(
                    jwt=token,
                    key=public_key,
                    algorithms=["RS256"],
                    issuer=spec.issuer,
                    audience=spec.client_id,
                    options={"verify_aud": True},
                ),
                allowed_roles=spec.allowed_roles,
            )
        except Exception as e:
            if isinstance(e, jwt.exceptions.InvalidTokenError) or isinstance(e, requests.HTTPError):
                if retry:
                    logger.debug(
                        "Error while decoding and verifying token, retrying with refreshed keys",
                        exc_info=True,
                    )
                    return self._decode_and_verify_jwt(token, spec, retry=False)

                logger.warning("Could not decode and verify token after retry", exc_info=True)
                raise InvalidTokenError("Could not decode and verify token")

            logger.exception("Error while decoding and verifying token", {"error": str(e)})
            raise Exception("Error while decoding and verifying token")

    def _get_public_key(self, token: str, decoded_token: Token) -> bytes:
        """_get_public_key gets the public key from the decoded token."""

        kid = jwt.get_unverified_header(token)["kid"]
        pk = RSAAlgorithm.from_jwk(json.dumps(decoded_token[kid]))
        if not isinstance(pk, RSAPublicKey):
            raise ValueError("The JWK does not represent a public key")

        return pk.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def _get_openid_keys(self, url: str, force_refresh: bool = False) -> Token:
        """_get_openid_keys either gets the OpenID keys from the cache or fetches the OpenID keys from the OpenID provider."""
        if not self._need_refresh(force_refresh, url):
            return self.cache[url]

        with self.mutex:
            if not self._need_refresh(force_refresh, url):
                return self.cache[url]
            if force_refresh:
                logger.debug("Forced refresh of keys")

            openid_keys = self._fetch_openid_keys(url)
            self.cache[url] = openid_keys

        return openid_keys

    def _fetch_openid_keys(self, url: str) -> Token:
        """_fetch_openid_keys fetches the OpenID keys from the OpenID provider."""
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        keys: Optional[Iterable[dict[str, Any]]] = cast(dict[str, Any], resp.json()).get("keys", None)
        if not keys:
            logger.error("No keys found in response")
            raise ValueError("No keys found in the response")

        return {key["kid"]: key for key in keys}

    def _get_issuer(self, token: Token) -> str:
        """_get_issuer gets the issuer from the token."""
        return token["iss"]

    def _need_refresh(self, force: bool, url: str) -> bool:
        """_need_refresh checks if the OpenID keys of the OpenID provider need to be refreshed."""
        return force or url not in self.cache


class Azure(TokenProvider):
    """Azure is a token provider for Azure Managed Identity."""

    def __init__(self, tenant: str, client_id: str, allowed_roles: Optional[List[str]]):
        self.allowed_roles = allowed_roles
        self.tenant = tenant
        self.client_id = client_id

    def matches_issuer(self, issuer: str) -> bool:
        """matches_issuer checks if the issuer matches the Azure Managed Identity issuer."""
        if self._same_tenant():
            return issuer.startswith("https://sts.windows.net/")
        return issuer == f"https://sts.windows.net/{self.tenant}/"

    def get_spec(self) -> ProviderSpec:
        """get_spec returns the ProviderSpec for Azure Managed Identity."""
        return ProviderSpec(
            url=f"https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys",
            client_id=self.client_id,
            allowed_roles=AllowedRoles(key="roles", roles=self.allowed_roles),
            issuer=f"""https://sts.windows.net/{self.tenant if not self._same_tenant() else "*"}/""",
            verify_token=None,
            same_tenant=self._same_tenant(),
        )

    def _same_tenant(self) -> bool:
        """_same_tenant checks if the tenant is the same as the client."""
        return self.tenant == "same"


class ICU(TokenProvider):
    """ICU is a token provider for the ICU OpenID provider."""

    def __init__(self, url: str, client_id: str, allowed_roles: Optional[List[str]]):
        self.allowed_roles = allowed_roles
        self.url = url
        self.client_id = client_id

    def matches_issuer(self, issuer: str) -> bool:
        """matches_issuer checks if the issuer matches the ICU OpenID provider."""
        return issuer == self.url

    def get_spec(self) -> ProviderSpec:
        """get_spec returns the ProviderSpec for the ICU OpenID provider."""
        return ProviderSpec(
            url=f"{self.url}/protocol/openid-connect/certs",
            client_id=self.client_id,
            allowed_roles=AllowedRoles(key="permission", roles=self.allowed_roles),
            issuer=self.url,
            verify_token=self.verify_token,
        )

    def verify_token(self, token: str, public_key: bytes) -> Token:
        """verify_token verifies the token using the public key."""
        tk: Token = jwt.decode(
            jwt=token,
            key=public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            issuer=self.url,
        )
        if tk.get("azp") != self.client_id:
            raise InvalidTokenError("Token could not be verified, invalid audience")
        return tk
