import os
from typing import Any
from typing import Dict

from azure.identity._constants import EnvironmentVariables
from azure.identity.aio import AzureCliCredential
from azure.identity.aio import AzureDeveloperCliCredential
from azure.identity.aio import AzurePowerShellCredential
from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import DefaultAzureCredential
from azure.identity.aio import EnvironmentCredential
from azure.identity.aio import ManagedIdentityCredential
from azure.identity.aio import WorkloadIdentityCredential
from clients._auth import OpenIDClient
from clients._openai import OpenAIClient
from clients._search import AzureSearchClient
from clients._storage import AzureStorageClient
from config import Config


def initialize_clients(cfg: Config) -> Dict[str, Any]:
    """initialize_clients initializes all the clients."""

    credential = new_credential_chain()

    return {
        "AuthClient": OpenIDClient(cfg.auth),
        "LLMClient": OpenAIClient(cfg.azure.openai, credential),
        "StorageClient": AzureStorageClient(cfg.azure.storage, credential),
        "SearchClient": AzureSearchClient(cfg.azure.search, credential),
    }


def new_credential_chain() -> ChainedTokenCredential:
    """new_credential_chain creates a new credential chain."""
    # We're not using the DefaultAzureCredential chain because we want to avoid the default behavior of
    # using the ManagedIdentityCredential on Azure Virtual Machines. There it uses the
    # ManagedIdentityCredential's fallback subclass ImdsCredential which only authenticates with to
    # resources of the same resource group. When we are on an Azure Virtual Machine, we want to use
    # the AzureDeveloperCliCredential instead, to use the right service principal.
    #
    # On production, the AzureDeveloperCliCredential is not available, so it naturally follows the rest of the chain,
    # which falls back to the ManagedIdentityCredential. This will then be the right choice, because the
    # app service is in the same resource group as the other resources.
    #
    # You can read more about the ChainedTokenCredential and the DefaultAzureCredential here:
    # https://github.com/Azure/azure-sdk-for-python/blob/azure-search-documents_11.4.0/sdk/identity/azure-identity/README.md#key-concepts

    if os.getenv("AZURE_USE_DEFAULT_CREDENTIAL", "true").lower() == "true":
        return DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    # We need to set _within_dac=True to avoid a warning about unset environment variables.
    env_cred = EnvironmentCredential(_within_dac=True)
    mi_cred = ManagedIdentityCredential()
    az_cred = AzureCliCredential()
    ps_cred = AzurePowerShellCredential()
    azd_cred = AzureDeveloperCliCredential()
    if all(os.getenv(var) for var in EnvironmentVariables.WORKLOAD_IDENTITY_VARS):
        workload_cred = WorkloadIdentityCredential()
        return ChainedTokenCredential(azd_cred, env_cred, workload_cred, mi_cred, az_cred, ps_cred)
    return ChainedTokenCredential(azd_cred, env_cred, mi_cred, az_cred, ps_cred)
