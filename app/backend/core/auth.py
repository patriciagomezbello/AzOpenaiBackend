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

# set debug mode
DEBUG = False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False")
if DEBUG_MODE == "True":
    DEBUG = True


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
        cache: A cache of OpenID keys.
        cache_lock: A lock to ensure thread-safe access to the cache.
    """

    def __init__(self):
        # Initialize the Auth class with environment variables and cache settings
        self.ALLOWED_ROLE = os.getenv("AZURE_AUTH_ROLE", "all")
        self.AUTH_CLIENT = os.getenv("AZURE_AUTH_CLIENT")
        self.AUTH_CLIENT_TENANT = os.getenv("AZURE_AUTH_TENANT", "same")
        self.cache = TTLCache(maxsize=10, ttl=3600)
        self.cache_lock = Lock()

    def fetch_openid_keys(self):
        # Fetch OpenID keys from the Microsoft Azure endpoint
        # TODO: generic openid enpoint for other providers
        openid_url = f"https://login.microsoftonline.com/{self.AUTH_CLIENT_TENANT}/discovery/v2.0/keys"
        keys = requests.get(openid_url).json()["keys"]
        if DEBUG:
            applicationLog("keys fetched from openid endpoint")
        return {key["kid"]: key for key in keys}

    def get_openid_keys(self, force_refresh=False):
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

            openid_keys = self.fetch_openid_keys()
            if DEBUG:
                applicationLog("keys fetched and stored in cache")
            self.cache["openid_keys"] = openid_keys

        return openid_keys

    def decode_and_verify_jwt(self, token, retry=False):
        # Decode and verify a JWT token using OpenID keys
        try:
            kid = jwt.get_unverified_header(token)["kid"]
            openid_keys = self.get_openid_keys()

            public_key_obj = RSAAlgorithm.from_jwk(json.dumps(openid_keys[kid]))

            if isinstance(public_key_obj, RSAPublicKey):
                public_key_pem = public_key_obj.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            else:
                raise ValueError("The JWK does not represent a public key")

            payload = jwt.decode(
                token,
                public_key_pem,
                algorithms=["RS256"],
                audience=self.AUTH_CLIENT,
                issuer=f"https://sts.windows.net/{self.AUTH_CLIENT_TENANT}/",
            )
            if DEBUG:
                applicationLog("token decoded and verified")
            return payload
        except jwt.exceptions.InvalidTokenError:
            if retry:
                if DEBUG:
                    applicationLog(
                        "Invalid token error, retrying with refreshed keys..."
                    )
                self.get_openid_keys(force_refresh=True)
                return self.decode_and_verify_jwt(token=token)
            else:
                applicationLog("Invalid token error after retry", "exc")
                return "InvalidTokenError"
        except Exception as e:
            applicationLog(str(e), "exc")
            return "Error"

    def decode_token(self, token):
        # Decode a token without verifying its signature
        try:
            if self.AUTH_CLIENT_TENANT != "same":
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

    def is_authorized(self, request):
        # Check if the request is authorized based on the token and allowed role
        if self.AUTH_CLIENT_TENANT == "same" and self.ALLOWED_ROLE == "all":
            return True

        auth_header = request.headers.get("Authorization")
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

        if (self.ALLOWED_ROLE != "all") and (
            self.ALLOWED_ROLE not in decoded_token["roles"]
        ):
            return False

        return True
