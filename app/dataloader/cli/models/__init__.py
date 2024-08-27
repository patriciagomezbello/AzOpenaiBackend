import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.models.config import CategoryRBACMap
    from cli.models.config import CLIConfig
    from cli.models.config import WebLoaderConfig


__all__ = [
    "CategoryRBACMap",
    "CLIConfig",
    "WebLoaderConfig",
]


_module_lookup = {
    "CategoryRBACMap": "cli.models.config",
    "CLIConfig": "cli.models.config",
    "LangchainConfig": "cli.models.config",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
