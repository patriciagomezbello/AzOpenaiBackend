from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional

from quart import Request


__all__ = ["AuthService"]


class AuthService(ABC):
    """AuthService provides an interface for interacting with the authentication service."""

    @abstractmethod
    def is_authenticated(self, request: Request) -> bool: ...

    @abstractmethod
    def is_authorized(self, request: Request) -> bool: ...

    @abstractmethod
    def get_roles(self, request: Request) -> Optional[List[str]]: ...
