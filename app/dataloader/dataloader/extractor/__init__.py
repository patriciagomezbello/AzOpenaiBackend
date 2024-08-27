import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.extractor.azure import DocumentIntelligence


__all__ = [
    "DocumentIntelligence",
]


_module_lookup = {
    "DocumentIntelligence": "dataloader.extractor.azure",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
