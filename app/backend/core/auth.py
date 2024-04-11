from quart import Request
import requests
import jwt
import json
import os
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cachetools import TTLCache
from threading import Lock
from core.modelhelper import applicationLog
from enum import Enum

# set debug mode
DEBUG = False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False")
if DEBUG_MODE == "True":
    DEBUG = True


class Auth_Provider(Enum):
    AZURE = "azure"
    OIDC = "oidc"


class Auth:
    """
    The Auth class encapsulates the authentication logic for the application.

    It uses environment variables to configure the allowed role and the Azure
    authentication client and tenant. It also maintains a cache of OpenID keys
    to avoid fetching them from the OpenID endpoint for every request.

    Attributes:
        ALLOWED_ROLE: The role that is allowed to access the application.
        AUTH_CLIENT: The Azure authentication client.
        AUTH_CLIENT_TENANT: The Azure authentication tenant.
        AUTH_OIDC_CLIENT: The OIDC authentication client.
        AUTH_OIDC_ISSUER_URL: The OIDC authentication issuer URL.
        cache: A cache of OpenID keys.
        cache_lock: A lock to ensure thread-safe access to the cache.
    """

    def __init__(self):
        # Initialize the Auth class with environment variables and cache settings
        self.ALLOWED_ROLE = os.getenv("AZURE_AUTH_ROLE", "all")
        self.AUTH_CLIENT = os.getenv("AZURE_AUTH_CLIENT")
        self.AUTH_CLIENT_TENANT = os.getenv("AZURE_AUTH_TENANT", "same")
        self.AUTH_OIDC_CLIENT = os.getenv("AZURE_AUTH_OIDC_CLIENT")
        self.AUTH_OIDC_ISSUER_URL = os.getenv("AZURE_AUTH_OIDC_ISSUER_URL")
        self.cache = TTLCache(maxsize=10, ttl=3600)
        self.cache_lock = Lock()

    def fetch_openid_keys(self, auth_type: str):
        # Fetch OpenID keys from the respective endpoint based on the auth type

        if (
            auth_type == Auth_Provider.OIDC.value
            and self.AUTH_OIDC_ISSUER_URL is not None
        ):
            openid_url = f"{self.AUTH_OIDC_ISSUER_URL}/protocol/openid-connect/certs"

        else:
            openid_url = f"https://login.microsoftonline.com/{self.AUTH_CLIENT_TENANT}/discovery/v2.0/keys"

        keys_response = requests.get(openid_url)
        keys_response.raise_for_status()
        keys = keys_response.json().get("keys")
        if keys is None:
            raise ValueError("No keys found in the response")

        if DEBUG:
            applicationLog("keys fetched from openid endpoint")

        return {key["kid"]: key for key in keys}

    def get_openid_keys(self, auth_type, force_refresh=False):
        # Get OpenID keys from cache or fetch them if not present or force refresh is requested
        if "openid_keys" in self.cache and not force_refresh:
            if DEBUG:
                applicationLog("keys fetched from cache")
            return self.cache["openid_keys"]

        with self.cache_lock:
            if "openid_keys" in self.cache and not force_refresh:
                if DEBUG:
                    applicationLog("keys fetched from cache after lock")
                return self.cache["openid_keys"]

            if force_refresh:
                if DEBUG:
                    applicationLog("Forced refresh of keys")

            openid_keys = self.fetch_openid_keys(auth_type)
            if DEBUG:
                applicationLog("keys fetched and stored in cache")
            self.cache["openid_keys"] = openid_keys

        return openid_keys

    def get_token_type(self, token: str) -> str:
        token_res = jwt.decode(
            jwt=token,
            algorithms=["RS256"],
            options={"verify_signature": False},
        )
        token_iss = token_res["iss"]

        return (
            Auth_Provider.OIDC.value
            if token_iss == self.AUTH_OIDC_ISSUER_URL
            else Auth_Provider.AZURE.value
        )

    def decode_and_verify_jwt(self, token: str, retry=False):
        # Decode and verify a JWT token using OpenID keys
        try:
            # check token_res wheter is

            kid = jwt.get_unverified_header(token)["kid"]
            openid_keys = self.get_openid_keys(auth_type=self.get_token_type(token))

            public_key_obj = RSAAlgorithm.from_jwk(json.dumps(openid_keys[kid]))

            if isinstance(public_key_obj, RSAPublicKey):
                public_key_pem = public_key_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            else:
                raise ValueError("The JWK does not represent a public key")

            # MSAL auth use case
            if self.get_token_type(token) == Auth_Provider.AZURE.value:
                payload = jwt.decode(
                    token,
                    public_key_pem,
                    algorithms=["RS256"],
                    audience=(
                        self.AUTH_CLIENT
                        if self.get_token_type(token) == Auth_Provider.AZURE.value
                        else self.AUTH_OIDC_CLIENT
                    ),
                    issuer=f"https://sts.windows.net/{self.AUTH_CLIENT_TENANT}/",
                )
            # OIDC (ICU) auth use case
            elif self.get_token_type(token) == Auth_Provider.OIDC.value:
                payload = jwt.decode(
                    token,
                    public_key_pem,
                    algorithms=["RS256"],
                    options={"verify_aud": False},
                    issuer=self.AUTH_OIDC_ISSUER_URL,
                )

                # authorized party check instead of audience check
                if payload.get("azp") != self.AUTH_OIDC_CLIENT:
                    raise jwt.InvalidTokenError("Invalid azp claim")

            if DEBUG:
                applicationLog("token decoded and verified")

            return payload
        except jwt.exceptions.InvalidTokenError:
            if retry:
                if DEBUG:
                    applicationLog(
                        "Invalid token error, retrying with refreshed keys..."
                    )
                self.get_openid_keys(
                    auth_type=self.get_token_type(token), force_refresh=True
                )
                return self.decode_and_verify_jwt(token=token)
            else:
                applicationLog("Invalid token error after retry", "exc")
                return "InvalidTokenError"
        except Exception as e:
            applicationLog(str(e), "exc")
            return "Error"

    def decode_token(self, token: str):
        # Decode a token without verifying its signature
        try:
            if (
                self.AUTH_CLIENT_TENANT != "same"
                or self.get_token_type(token) == Auth_Provider.OIDC.value
            ):
                return self.decode_and_verify_jwt(token=token, retry=True)
            elif self.ALLOWED_ROLE != "all":
                try:
                    token_res = jwt.decode(
                        jwt=token,
                        algorithms=["RS256"],
                        options={"verify_signature": False},
                    )
                    if DEBUG:
                        applicationLog("token decoded")
                    return token_res
                except jwt.exceptions.InvalidTokenError:
                    applicationLog("Invalid token error", "exc")
                    return "InvalidTokenError"
        except Exception as e:
            applicationLog(str(e), "exc")

    # TODO: auth status, 401 or 403 (not just 403) needs to be returned in case Azure AppService Auth is not used

    def is_authorized(self, request: Request):
        # Check if the request is authorized based on the token and allowed role
        if self.AUTH_CLIENT_TENANT == "same" and self.ALLOWED_ROLE == "all":
            return True

        auth_header = request.headers.get("Authorization")

        if auth_header is None:
            applicationLog("no auth header, returning 403", "error")
            return False

        parts = auth_header.split()
        token = parts[1]

        decoded_token = self.decode_token(token)

        if (
            decoded_token == "InvalidTokenError"
            or decoded_token == "Error"
            or decoded_token is None
        ):
            applicationLog("invalid Token, returning 403", "error")
            return False

        if self.ALLOWED_ROLE != "all":
            token_key = (
                "permission"
                if self.get_token_type(token) == Auth_Provider.OIDC.value
                else "roles"
            )
            if DEBUG:
                applicationLog(f"Token Key: {token_key}")

            allowed_roles = [role.strip() for role in self.ALLOWED_ROLE.split(",")]

            for role in allowed_roles:
                if role in decoded_token[token_key]:
                    return True

            return False

        return True
