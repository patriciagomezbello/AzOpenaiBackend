import asyncio
import os
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Sequence
from typing import Any

from azure.identity.aio import AzureDeveloperCliCredential
from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import DefaultAzureCredential
from cli.core.parser import ParsedArgs
from cli.core.service import Service
from cli.core.utils import defer
from cli.models import CLIConfig
from dataloader.base import new_logger
from dataloader.indexer import Indexer
from dataloader.indexer.models import DocumentInfo
from dataloader.loaders import BlobInteractor


logger = new_logger(__name__)


def obtain_credential() -> ChainedTokenCredential:
    """Creates a new ChainedTokenCredential with the default credential chain."""
    if os.getenv("AZURE_USE_DEFAULT_CREDENTIAL", "true").lower() == "true":
        logger.info("Using default Azure credential chain.")
        return DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    logger.info("Using custom Azure credential chain.")
    return ChainedTokenCredential(
        AzureDeveloperCliCredential(),
        DefaultAzureCredential(exclude_workload_identity_credential=True, exclude_managed_identity_credentials=True),
    )


async def execute(args: ParsedArgs) -> None:
    credential = obtain_credential()
    config = CLIConfig.load(args)
    logger.info("Starting data loader with the provided configuration.", extra={"config": config.model_dump()})

    service = Service(
        BlobInteractor(account=config.storage_account, container=config.docs_container, credential=credential),
        Indexer(config=config.indexer_config, credential=credential),
        config,
    )

    loading_modes: dict[str, list[Callable[[], Coroutine[Any, Any, tuple[Sequence[DocumentInfo], dict[str, int]]]]]] = {
        "file": [service.load_file_mode],
        "lc": [service.load_lc_mode],
        "all": [service.load_file_mode, service.load_lc_mode],
    }

    loaders = loading_modes.get(config.data_mode, [])
    async with defer(service.close, lambda e: logger.exception(f"An error occurred while running the data loader: {e}")):
        documents: Sequence[DocumentInfo] = []
        summary: dict[str, int] = {}

        if config.reset_index:
            await service.indexer.delete_index(service.indexer.searcher._index_name)
            if await service.blob_interactor.container_client.exists():
                await service.blob_interactor.container_client.delete_container()
                # To avoid a ContainerBeingDeleted error during runtime, we need to wait for the container to be deleted.
                # For more information, see https://stackoverflow.com/a/34748439
                await asyncio.sleep(60)

        for load in loaders:
            docs, sum = await load()
            documents.extend(docs)
            summary.update(sum)

        await service.purge_chunk_corpses(summary)
        # await service.purge_doc_corpses(documents)
