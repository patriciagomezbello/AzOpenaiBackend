from collections.abc import AsyncGenerator
from collections.abc import Generator

from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import WebDocument


class WebDocumentLoader:
    def __init__(self, _: LoaderConfig):
        raise NotImplementedError(f"Loader {self.__class__.__name__}.__init__() not implemented.")

    def load(self) -> list[WebDocument]:
        return list(self.lazy_load())

    async def aload(self) -> list[WebDocument]:
        return [doc async for doc in self.alazy_load()]

    def lazy_load(self) -> Generator[WebDocument, None, None]:
        for doc in []:
            yield doc
        raise NotImplementedError(f"Loader {self.__class__.__name__}.{self.lazy_load.__name__}() not implemented.")

    async def alazy_load(self) -> AsyncGenerator[WebDocument, None]:
        for doc in self.lazy_load():
            yield doc
