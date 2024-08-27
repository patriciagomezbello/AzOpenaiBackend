import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.indexer.index import Indexer
    from dataloader.indexer.index import DocumentChunker
    from dataloader.indexer.index import Splitter
    from dataloader.indexer.language import LanguageDetector


__all__ = [
    "Indexer",
    "DocumentChunker",
    "Splitter",
    "LanguageDetector",
]


_module_lookup = {
    "Indexer": "dataloader.indexer.index",
    "DocumentChunker": "dataloader.indexer.index",
    "Splitter": "dataloader.indexer.index",
    "LanguageDetector": "dataloader.indexer.language",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
