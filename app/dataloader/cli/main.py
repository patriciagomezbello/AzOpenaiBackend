import os
from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

from azure.identity.aio import AzureDeveloperCliCredential
from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import DefaultAzureCredential
from cli.core.parser import ParsedArgs
from cli.core.service import Service
from cli.core.utils import defer
from cli.models import CLIConfig
from dataloader.base import new_logger
from dataloader.indexer.index import Indexer
from dataloader.loaders.blob import BlobInteractor


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


async def main(args: ParsedArgs) -> None:
    credential = obtain_credential()
    config = CLIConfig.load(args)
    logger.info(f"Starting data loader with config: {config.model_dump()}")

    service = Service(
        BlobInteractor(account=config.storage_account, container=config.docs_container, credential=credential),
        Indexer(config=config.indexer_config, credential=credential),
        config,
    )

    loading_modes: dict[str, list[Callable[[bool], Coroutine[Any, Any, None]]]] = {
        "file": [service.load_file_mode],
        "lc": [service.load_lc_mode],
        "all": [service.load_file_mode, service.load_lc_mode],
    }

    loaders = loading_modes.get(config.data_mode, [])

    async with defer(service.close, lambda e: logger.exception(f"An error occurred while running the data loader: {e}")):
        reset_status = False
        for load in loaders:
            await load(reset_status)
            # After the first loader is finished, we don't need to reset the index anymore
            if config.reset_index:
                reset_status = True
            config.reset_index = False
