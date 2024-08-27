import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.loaders.blob import BlobInteractor
    from dataloader.loaders.langchain import LangchainLoader
    from dataloader.loaders.magentainfos import MagentaInfosLoader
    from dataloader.loaders.staffbase import StaffbaseLoader


__all__ = [
    "BlobInteractor",
    "LangchainLoader",
    "MagentaInfosLoader",
    "StaffbaseLoader",
]


_module_lookup = {
    "BlobInteractor": "dataloader.loaders.blob",
    "LangchainLoader": "dataloader.loaders.langchain",
    "MagentaInfosLoader": "dataloader.loaders.magentainfos",
    "StaffbaseLoader": "dataloader.loaders.staffbase",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
