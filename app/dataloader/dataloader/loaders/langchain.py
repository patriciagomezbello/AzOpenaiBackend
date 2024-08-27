from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Generator

from dataloader.loaders.base import WebDocumentLoader
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import WebDocument


class LangchainLoader(WebDocumentLoader):
    def __init__(self, config: LoaderConfig):
        self.config = config
        self.loader = config.new_langchain_loader()

    def lazy_load(self) -> Generator[WebDocument, None, None]:
        for doc in self.loader.lazy_load():
            yield WebDocument.from_langchain(doc, self.config)

    async def alazy_load(self) -> AsyncGenerator[WebDocument, None]:
        async for doc in self.loader.alazy_load():
            yield WebDocument.from_langchain(doc, self.config)
