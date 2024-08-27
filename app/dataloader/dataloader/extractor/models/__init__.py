import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.extractor.models.base import Page
    from dataloader.extractor.models.config import ExtractorConfig


__all__ = [
    "Page",
    "ExtractorConfig",
]


_module_lookup = {
    "Page": "dataloader.extractor.models.base",
    "ExtractorConfig": "dataloader.extractor.models.config",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
