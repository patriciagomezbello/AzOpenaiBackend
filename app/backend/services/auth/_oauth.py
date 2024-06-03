from typing import List
from typing import Optional
from typing import Union

from clients import AuthClient
from clients import AuthenticatedToken
from clients import InvalidTokenError
from clients import UnknownProviderError
from quart import Request
from services.auth._interface import AuthService
from services.category import CategoryService
from services.logger import new_logger
from services.timer import timer


logger = new_logger(__name__)


class NoAuthHeaderError(Exception):
    """NoAuthHeaderError is an error that is raised when the Authorization header is missing."""

    pass


class NoRolesConfiguredError(Exception):
    """NoRolesConfiguredError is an error that is raised when no roles are configured."""

    pass


class OAuthService(AuthService):
    """OAuthService is a service that provides OAuth authentication and authorization."""

    def __init__(self, client: AuthClient, cat_svc: CategoryService):
        self.client = client
        self.cat_svc = cat_svc

    @timer()
    def is_authenticated(self, request: Request) -> bool:
        token = self._get_token(request)
        try:
            _ = self.client.decode_token(token)
        except Exception as e:
            if isinstance(e, InvalidTokenError) or isinstance(e, UnknownProviderError):
                logger.warning("Authentication failed", {"error": str(e)})
                return False
            raise

        return True

    @timer()
    def is_authorized(self, request: Request) -> bool:
        token = self._get_token(request)
        try:
            decoded = self.client.decode_token(token)
        except Exception as e:
            # Even though is_authorized should always be called after is_authenticated,
            # we should still handle the case to avoid potential security issues.
            if isinstance(e, InvalidTokenError) or isinstance(e, UnknownProviderError):
                logger.warning("Authorization failed", {"error": str(e)})
                return False
            raise

        return self._does_token_have_role(token, decoded.allowed_roles.roles)

    @timer()
    def get_roles(self, request: Request) -> Optional[List[str]]:
        token = self._get_token(request)
        try:
            decoded = self.client.decode_token(token)
        except Exception as e:
            if isinstance(e, InvalidTokenError) or isinstance(e, UnknownProviderError):
                logger.warning("Invalid Token", {"error": str(e)})
                return []
            raise

        return decoded.token.get(decoded.allowed_roles.key, [])

    def _get_token(self, request: Request) -> str:
        header = request.headers.get("Authorization")
        if header is None:
            logger.debug("No 'Authorization' header found")
            raise NoAuthHeaderError("Authorization header is missing")

        parts = header.split()
        token = parts[1] if len(parts) > 1 else None
        if token is None:
            logger.debug("Token is missing in 'Authorization' header")
            raise NoAuthHeaderError("Token is missing in Authorization header")

        return token

    def _does_token_have_role(self, token: Union[str, AuthenticatedToken], roles: Optional[List[str]]) -> bool:
        """_does_token_have_role checks if the token has the required roles."""

        if not roles:
            return True

        if isinstance(token, str):
            decoded = self.client.decode_token(token)
        else:
            decoded = token

        # Return True if the token has any of the required roles.
        return any(role in decoded.token.get(decoded.allowed_roles.key, []) for role in roles)
