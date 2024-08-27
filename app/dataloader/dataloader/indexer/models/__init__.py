import importlib
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataloader.indexer.models.document import AccessModel
    from dataloader.indexer.models.document import Document
    from dataloader.indexer.models.document import DocumentInfo
    from dataloader.indexer.models.index import ChunkerConfig
    from dataloader.indexer.models.index import DocumentChunk
    from dataloader.indexer.models.index import IndexerConfig
    from dataloader.indexer.models.index import TextSplitter
    from dataloader.indexer.models.language import SupportedLanguages
    from dataloader.indexer.models.language import SUPPORTED_LANGUAGES


__all__ = [
    "AccessModel",
    "Document",
    "DocumentInfo",
    "DocumentChunk",
    "IndexerConfig",
    "ChunkerConfig",
    "TextSplitter",
    "SupportedLanguages",
    "SUPPORTED_LANGUAGES",
]


_module_lookup = {
    "AccessModel": "dataloader.indexer.models.document",
    "Document": "dataloader.indexer.models.document",
    "DocumentInfo": "dataloader.indexer.models.document",
    "DocumentChunk": "dataloader.indexer.models.index",
    "IndexerConfig": "dataloader.indexer.models.index",
    "ChunkerConfig": "dataloader.indexer.models.index",
    "TextSplitter": "dataloader.indexer.models.index",
    "SupportedLanguages": "dataloader.indexer.models.language",
    "SUPPORTED_LANGUAGES": "dataloader.indexer.models.language",
}


def __getattr__(name: str) -> Any:
    if name in _module_lookup:
        module = importlib.import_module(_module_lookup[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")
