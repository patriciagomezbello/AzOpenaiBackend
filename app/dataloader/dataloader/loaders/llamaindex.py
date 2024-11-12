import os
from collections.abc import Generator

from dataloader.loaders.base import WebDocumentLoader
from dataloader.loaders.models import JiraConfig
from dataloader.loaders.models import LoaderConfig
from dataloader.loaders.models import WebDocument
from llama_index.readers.jira import JiraReader


class JiraLoader(WebDocumentLoader):
    def __init__(self, config: LoaderConfig) -> None:
        self.loader_config = config
        self.llama_index_reader_config = config._ensure_config(JiraConfig)
        self.reader = self._get_reader()

    def _get_reader(self) -> JiraReader:
        try:
            api_token = os.environ[self.llama_index_reader_config.token_ref]
        except KeyError:
            raise ValueError(f"Environment variable {self.llama_index_reader_config.token_ref} not found")

        return JiraReader(
            email=self.llama_index_reader_config.username, api_token=api_token, server_url=self.llama_index_reader_config.url
        )

    def lazy_load(self) -> Generator[WebDocument, None, None]:
        query = f"project = {self.llama_index_reader_config.project_key}"
        start = 0
        max_results = 100
        while True:
            docs = self.reader.load_langchain_documents(query=query, start_at=start, max_results=max_results)
            start += max_results
            if not docs:
                break

            for doc in docs:
                doc.metadata["source"] = doc.metadata["url"]
                yield WebDocument.from_langchain(doc, self.loader_config)
