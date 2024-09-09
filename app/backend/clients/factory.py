import os

from azure.identity.aio import AzureDeveloperCliCredential
from azure.identity.aio import ChainedTokenCredential
from azure.identity.aio import DefaultAzureCredential


def obtain_credential() -> ChainedTokenCredential:
    """obtain_credential returns a ChainedTokenCredential to authenticate against Azure services."""
    if os.getenv("AZURE_USE_DEFAULT_CREDENTIAL", "true").lower() == "true":
        return DefaultAzureCredential(exclude_shared_token_cache_credential=True)

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
    azd_cred = AzureDeveloperCliCredential()
    default_cred = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    return ChainedTokenCredential(azd_cred, default_cred)
