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
    - [Example](#example)
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
| `CORS_DISABLED`      | Whether to disable the CORS policy. **Use with caution!**                                                               | `false`       |           |

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
| `QUERY_SERVICE_TYPE`   | The type of the search service to use. Options: `default`, `extended`                                                                    | `default`     |           |

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

#### Example

<!-- markdownlint-disable MD033 -->
<details>

<summary>Example <code>.env</code> file</summary>

```properties
# Mate Configurations
# https://gitlab.devops.telekom.de/red-october/azure-search-openai-backend/-/tree/main/docs/dev#mate-configuration

# General Configuration
API_BASE_PATH=/
CORS_DISABLED=false

# Azure Services Configuration
AZURE_OPENAI_SERVICE=
AZURE_OPENAI_CHATGPT_DEPLOYMENT=
AZURE_OPENAI_CHATGPT_MODEL=
AZURE_OPENAI_EMB_DEPLOYMENT=

AZURE_SEARCH_SERVICE=
AZURE_SEARCH_INDEX=

AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_CONTAINER_DOCS=

AZURE_USE_DEFAULT_CREDENTIAL=false

# Chat Configuration
ABBREVIATIONS={"DTAG": "Deutsche Telekom AG"}

ANSWER_SYSTEM_PROMPT='You are an AI-Assistant for Telekom-internal topics. You have to answer the question abiding by the following rules:
- You will answer questions related to the prompted data that is retrieved beforehand.
- Take only the information provided in the prompt into account for your answer.
- Each source has a name followed by a colon. You have to always include the source name in front of the colon for information you use in the response. 
- Always use square brackets to reference the source and list each source separately, for example [data-1.pdf] or [https://telekom.de/data]. 
- Only include sources with ".pdf" at the end or "https://" in the beginning, never include anything else besides the source name in the square brackets. 
- In case of ambiguity regarding the questions ask clarifying questions back
- If there is nothing relevant provided in the prompt say {noidea}.
{injected_prompt}'

QUERY_SYSTEM_PROMPT='Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about questions.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames, links or numbers in brackets e.g. [1] or [3] in the search query terms.
    If the question is not in {language}, translate the question to {language} before generating the search query.'

MAX_TOKENS_ANSWER=1024
MAX_TOKENS_QUERY=32
QUERY_SERVICE_TYPE=default

# Authentication/Authorization Configuration
AZURE_AUTH_ROLE=all
AZURE_AUTH_CLIENT=
AZURE_AUTH_TENANT=same

AZURE_AUTH_ICU_CLIENT= # optional
AZURE_AUTH_ICU_ISSUER_URL= # optional

# Logging Configuration
LOG_LEVEL=info
LOG_FORMAT=json
LOG_CALLER=false
LOG_EXECUTION_TIMES=false
LOG_SENSITIVE_DATA=false
```

</details>
<!-- markdownlint-enable MD033 -->

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
