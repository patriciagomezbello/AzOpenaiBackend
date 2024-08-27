import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.loaders.models.base import BaseConfig
    from dataloader.loaders.models.blob import File
    from dataloader.loaders.models.constants import WEBLOADER_REGISTRY
    from dataloader.loaders.models.langchain import ConfluenceConfig
    from dataloader.loaders.models.langchain import DocusaurusConfig
    from dataloader.loaders.models.langchain import GitConfig
    from dataloader.loaders.models.langchain import WebsiteConfig
    from dataloader.loaders.models.magentainfos import MagentaInfosConfig
    from dataloader.loaders.models.staffbase import StaffbaseConfig
    from dataloader.loaders.models.webloader import LoaderConfig
    from dataloader.loaders.models.webloader import LoaderName
    from dataloader.loaders.models.webloader import WebDocument


__all__ = [
    "BaseConfig",
    "File",
    "WEBLOADER_REGISTRY",
    "ConfluenceConfig",
    "DocusaurusConfig",
    "GitConfig",
    "WebsiteConfig",
    "MagentaInfosConfig",
    "StaffbaseConfig",
    "LoaderConfig",
    "LoaderName",
    "WebDocument",
]


_module_lookup = {
    "File": "dataloader.loaders.models.blob",
    "WEBLOADER_REGISTRY": "dataloader.loaders.models.constants",
    "BaseConfig": "dataloader.loaders.models.langchain",
    "ConfluenceConfig": "dataloader.loaders.models.langchain",
    "DocusaurusConfig": "dataloader.loaders.models.langchain",
    "GitConfig": "dataloader.loaders.models.langchain",
    "WebsiteConfig": "dataloader.loaders.models.langchain",
    "MagentaInfosConfig": "dataloader.loaders.models.magentainfos",
    "StaffbaseConfig": "dataloader.loaders.models.staffbase",
    "LoaderConfig": "dataloader.loaders.models.webloader",
    "LoaderName": "dataloader.loaders.models.webloader",
    "WebDocument": "dataloader.loaders.models.webloader",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
