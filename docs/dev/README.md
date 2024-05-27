# Development Guide<!-- omit in toc -->

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Testing](#testing)
- [Run locally](#run-locally)
  - [Azure Configuration](#azure-configuration)
  - [Mate Configuration](#mate-configuration)
    - [General Configuration](#general-configuration)
    - [Azure Services Configuration](#azure-services-configuration)
    - [Chat Configuration](#chat-configuration)
    - [Authentication Configuration](#authentication-configuration)
    - [Logging Configuration](#logging-configuration)
  - [Run the application](#run-the-application)
    - [Run the backend only](#run-the-backend-only)
    - [Run the whole application](#run-the-whole-application)
    - [Deploy the infrastructure](#deploy-the-infrastructure)
    - [Deploy the backend](#deploy-the-backend)
    - [Update the storage data](#update-the-storage-data)

## Prerequisites

In order to develop Mate, you need to have the following prerequisites:

- [Python 3.11](https://www.python.org/downloads/) or higher (we recommend using [pyenv](https://github.com/pyenv/pyenv))
- [Flake8](https://flake8.pycqa.org/en/latest/) Linter
- [Black](https://black.readthedocs.io/en/stable/getting_started.html) Formatter
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)

Optional:

- [Make](https://www.gnu.org/software/make/) - For running the Makefile commands
- [pre-commit](https://pre-commit.com/#installation) - For running the pre-commit hooks
- [gitlab-ci-local](https://github.com/firecow/gitlab-ci-local) - For testing the GitLab CI locally

## Architecture

To learn more about the architecture of Mate, please refer to the [architecture](./repository.md) documentation.

## Testing

To run the tests, you can use the following command:

```bash
make mate-test
```

## Run locally

Before running the application locally, you need to set up the azure and mate configuration.

### Azure Configuration

To be able to use the Azure services locally, you need to set up the Azure configuration.

1. Log in to Azure using the Azure CLI:

    ```bash
    az login
    ```

2. Log in to the Azure Developer CLI:

    ```bash
    azd auth login
    ```

3. Add the azure configuration to `./.azure/config.json`:

    ```json
    {
        "version": 1,
        "defaultEnvironment": "<AZURE_ENV_NAME>"
    }
    ```

    Replace `<AZURE_ENV_NAME>` with the `azd-env-name` tag of your Azure Resource Group.

4. Add the environment configuration to `./.azure/<AZURE_ENV_NAME>/config.json`:

    ```json
    {
        "infra": {
            "parameters": {
            "openAiResourceGroupLocation": "<OpenAILocation>"
            }
        }
    }
    ```

    Replace `<OpenAILocation>` with the location of the OpenAI resource group (e.g. `westeurope`, `swedencentral`, etc.).

5. Add a `.env` file to `./.azure/<AZURE_ENV_NAME>` with the [`ENVIRONMENT` configuration](/docs/deployment.md#file-environment).

6. Add the [`CONTEXT` configuration](/docs/deployment.md#file-context) to `./app/backend/core/context.py`.

### Mate Configuration

To configure the Mate application, you need to set up the environment variables. You can do this by creating the `.env` file mentioned before in the [Azure configuration](#azure-configuration).

Our configuration is split into different sections, each with its own set of environment variables. The following sections are available:

- [General Configuration](#general-configuration)
- [Azure Services Configuration](#azure-services-configuration)
- [Chat Configuration](#chat-configuration)
- [Authentication Configuration](#authentication-configuration)

#### General Configuration

The general configuration is used to set up the basic configuration of the application. The following environment variables are available:

| Environment Variable | Description                                                                                                             | Default Value | Mandatory |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------- | --------- |
| `API_BASE_PATH`      | The base path of the API. The version will be appended automatically except if the version is set to its default value. | `/`           |           |

#### Azure Services Configuration

The Azure services configuration is used to set up the connection to the Azure services. The following environment variables are available:

| Environment Variable              | Description                                                                                                                                                                              | Default Value | Mandatory |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | --------- |
| `AZURE_OPENAI_SERVICE`            | The name of the Azure OpenAI service resource.                                                                                                                                           |               | X         |
| `AZURE_OPENAI_CHATGPT_DEPLOYMENT` | The name of the Azure OpenAI ChatGPT deployment.                                                                                                                                         |               | X         |
| `AZURE_OPENAI_CHATGPT_MODEL`      | The name of the Azure OpenAI ChatGPT model.                                                                                                                                              |               | X         |
| `AZURE_OPENAI_EMB_DEPLOYMENT`     | The name of the Azure OpenAI embedding deployment.                                                                                                                                       |               | X         |
| `AZURE_SEARCH_SERVICE`            | The name of the Azure Search service resource.                                                                                                                                           |               | X         |
| `AZURE_SEARCH_INDEX`              | The name of the Azure Search index.                                                                                                                                                      |               | X         |
| `AZURE_STORAGE_ACCOUNT`           | The name of the Azure Storage account.                                                                                                                                                   |               | X         |
| `AZURE_STORAGE_CONTAINER_DOCS`    | The name of the Azure Storage container for docs.                                                                                                                                        |               | X         |
| `AZURE_USE_DEFAULT_CREDENTIAL`    | Whether to use the [Azure Default Credential Chain](https://github.com/Azure/azure-sdk-for-python/blob/azure-search-documents_11.4.0/sdk/identity/azure-identity/README.md#key-concepts) | `true`        |           |

#### Chat Configuration

The chat configuration is used to set up the chat conversation. The following environment variables are available:

| Environment Variable   | Description                                                                                                                              | Default Value | Mandatory |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------- | --------- |
| `ABBREVIATIONS`        | A list of abbreviations that should be replaced with their full form. The list should be in json format: `{"abbreviation": "full form"}` | `{}`          | X         |
| `ANSWER_SYSTEM_PROMPT` | The system message for the chat conversation                                                                                             |               | X         |
| `QUERY_SYSTEM_PROMPT`  | The query prompt for enhancing the search keywords for the knowledge base                                                                |               | X         |
| `MAX_TOKENS_ANSWER`    | The maximum number of tokens for the answer                                                                                              | `1024`        |           |
| `MAX_TOKENS_QUERY`     | The maximum number of tokens for the query                                                                                               | `32`          |           |

#### Authentication Configuration

The authentication configuration is used to set up the authentication for the application. The following environment variables are available:

| Environment Variable        | Description                                                                                                         | Default Value | Mandatory |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------- | --------- |
| `AZURE_AUTH_ROLE`           | The allowed roles for authorization. Multiple roles can be separated by a comma. On default, all roles are allowed. | `all`         |           |
| `AZURE_AUTH_CLIENT`         | The client ID of the Managed Identity for which the token is requested for.                                         |               | X         |
| `AZURE_AUTH_TENANT`         | The tenant ID of the Managed Identity for which the token is requested for. If not set, the same tenant is used.    | `same`        |           |
| `AZURE_AUTH_ICU_CLIENT`     | The client ID of the ICU OpenID Connect client.                                                                     |               |           |
| `AZURE_AUTH_ICU_ISSUER_URL` | The issuer URL of the ICU OpenID Connect realm.                                                                     |               |           |

In case you need another Open ID Connect Provider, you can open an [issue](https://gitlab.devops.telekom.de/red-october/azure-search-openai-backend/-/issues) to discuss your requirements or append your own provider to the [authentication client](/app/backend/clients/_auth.py) and open a merge request.

#### Logging Configuration

| Environment Variable  | Description                                                                          | Default Value | Mandatory |
| --------------------- | ------------------------------------------------------------------------------------ | ------------- | --------- |
| `LOG_LEVEL`           | The log level of the application.                                                    | `INFO`        |           |
| `LOG_CALLER`          | Whether to log the caller of the log message.                                        | `false`       |           |
| `LOG_FORMAT`          | Format of the log messages. Options: `color`, `text`, `json`.                        | `json`        |           |
| `LOG_EXECUTION_TIMES` | Whether to log the execution times of each method. Needs `LOG_LEVEL` set to `DEBUG`. | `false`       |           |
| `LOG_SENSITIVE_DATA`  | Whether to log sensitive data. Needs `LOG_LEVEL` set to `DEBUG`.                     | `false`       |           |

### Run the application

Now you're ready to run the application. To do so, we recommend using the Makefile commands.

To get a list of all available commands, you can run `make help`.

#### Run the backend only

```bash
# To run the backend only
make mate
```

#### Run the whole application

```bash
# To run the whole application
make dev
```

This may not work if you haven't set up the `./frontend.env` file for the frontend. For more information about the configuration, please refer to the [frontend documentation](https://gitlab.devops.telekom.de/red-october/telit-azure-openai-gpt-frontend#run-the-application).

#### Deploy the infrastructure

If you haven't already deployed the infrastructure, you can do so by running the following command:

```bash
# deploys backend to app service
azd provision
```

#### Deploy the backend

To deploy the backend to the Azure App Service, you can run the following command:

```bash
# bundles backend, deploys infrastructure and
# deploys backend to app service
azd up
```

#### Update the storage data

In order to sync the local data with the storage account, you can run the following command:

```bash
./scripts/prepdocs.sh
```

This will upload the data from the `./data` directory to the storage account. It will also convert data in the `./data2convert` directory to the required format and upload it to the storage account.
