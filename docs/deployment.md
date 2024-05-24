# Deployment Guide<!-- omit in toc -->

To deploy your own instance of Mate, follow the steps below.

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
  - [CI/CD Variables](#cicd-variables)
  - [File Variables](#file-variables)
    - [File: `ENVIRONMENT`](#file-environment)
      - [Variables](#variables)
      - [Example](#example)
    - [File: `CONTEXT`](#file-context)
      - [Variables](#variables-1)
      - [Example](#example-1)
    - [File: `ABBREV`](#file-abbrev)
      - [Example](#example-2)
- [Known Issues](#known-issues)

## Prerequisites

**Before using your own instance of Mate, you need to have the prerequisites described in the [main documentation](/docs/README.md#prerequisites).**

## Configuration

Before deploying Mate, you need to set the variables below in your GitLab project to configure the deployment.

### CI/CD Variables

| Variable              | Description                                                                                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OpenAILocation`      | Available regions are: `francecentral`, `swedencentral`, `westeurope`                                                                                                |
| `REPO_URL`            | The URL of the data repository (e.g. `https://gitlab.devops.telekom.de/red-october/ccoe-data`)                                                                       |
| `ACCESS_TOKEN`        | The access token for the data repository ([How-To Guide](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html#create-a-project-access-token)) |
| `AZURE_CLIENT_ID`     | The service principal id                                                                                                                                             |
| `AZURE_CLIENT_SECRET` | The service principal secret                                                                                                                                         |
| `AZURE_TENANT_ID`     | The tenant id (e.g. `628242bd-7e70-4aa9-8ee1-72586b4540fe` for the DTIT tenant)                                                                                      |
| `RUNNER_NAME`         | The name of the provisioned private GitLab runner in the same subscription                                                                                           |
| `RUNNER_RG`           | The resource group name of the provisioned private gitlab runner in the same subscription                                                                            |
| `RUNNER_TAG`          | The tag of the provisioned private gitlab runner in the same subscription                                                                                            |
| `SUBSCRIPTION_ID`     | The id of the subscription                                                                                                                                           |

### File Variables

You also need to set the following file variables in your GitLab project:

#### File: `ENVIRONMENT`

The environment file is a `.env` file that contains the environment variables for the deployment.

<!-- markdownlint-disable MD024 -->
##### Variables
<!-- markdownlint-enable MD024 -->

| Variable                             | Description                                                                                          | Mandatory |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------- | --------- |
| `AZURE_AUTH_CLIENT`                  | The client id of the app registration used for authentication                                        | X         |
| `AZURE_ENV_NAME`                     | The name of the environment                                                                          | X         |
| `AZURE_SUBSCRIPTION_ID`              | The id of the subscription                                                                           | X         |
| `AZURE_TENANT_ID`                    | The tenant id                                                                                        | X         |
| `AZURE_LOCATION`                     | The location of the resources                                                                        | X         |
| `AZURE_VNET_RESOURCE_GROUP`          | The resource group of the existing VNet                                                              | X         |
| `AZURE_VNET_NAME`                    | The name of the existing VNet                                                                        | X         |
| `AZURE_SUBNET_NAME`                  | The name of the existing subnet inside the existing VNet                                             | X         |
| `AZURE_SUBNET_NAME_APPSERVICE`       | The name of the existing subnet inside the existing VNet for the App Service                         | X         |
| `AZURE_ALLOWED_CORS`                 | The list of allowed CORS origins                                                                     | X         |
| `AZURE_OPENAI_CHATGPT_MODEL_NAME`    | The name of the OpenAI ChatGPT model (e.g. `gpt-35-turbo`, `gpt-35-turbo-16k`, `gpt-4`, `gpt-4-32k`) |           |
| `AZURE_OPENAI_CHATGPT_MODEL_VERSION` | The version of the OpenAI ChatGPT model (e.g. `0613`, `0914`)                                        |           |
| `AZURE_AUTH_ROLE`                    | The allowed Azure AD role (if not set all authenticated users can access)                            |           |
| `AZURE_AUTH_TENANT`                  | The tenant ID of the Azure AD (only required if `AZURE_AUTH_ROLE` is set and another tenant is used) |           |
| `AZURE_APPSERVICE_SKU`               | The SKU of the App Service (e.g. `B1`, `B2`, `B3`, `S1`,`S2`, `S3`, `P1`, `P2`, `P3`, `P4`)          |           |
| `AZURE_SEARCH_SERVICE_SKU`           | The SKU of the Azure Search service (e.g. `basic`, `standard`, `standard2`, `standard3`)             |           |
| `AZURE_REDEPLOY_OPENAI`              | Set to `true` to redeploy the OpenAI instance (temporary bugfix)                                     |           |

##### Example

```properties
AZURE_AUTH_ClIENT="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_ENV_NAME="azure-search-openai-dev-env-name"
AZURE_SUBSCRIPTION_ID="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_TENANT_ID="628242bd-7e70-4aa9-8ee1-72586b4540fe"
AZURE_LOCATION="westeurope"
AZURE_VNET_RESOURCE_GROUP="rg-ci-vnet"
AZURE_VNET_NAME="vnet_dtit_cix00xx"
AZURE_SUBNET_NAME="sn-standard"
AZURE_SUBNET_NAME_APPSERVICE="sn-appservice"
AZURE_ALLOWED_CORS="https://your.ui.url,https://yourother.ui.url"
AZURE_OPENAI_CHATGPT_MODEL_NAME="gpt-35-turbo"
AZURE_OPENAI_CHATGPT_MODEL_VERSION="0613"
AZURE_AUTH_ROLE="Model.User"
AZURE_AUTH_TENANT="bde4dffc-4b60-4cf6-8b04-a5eeb25f5c4f"
AZURE_APPSERVICE_SKU="B1"
AZURE_SEARCH_SERVICE_SKU="standard"
```

#### File: `CONTEXT`

The context file is a python file that contains the context for the large language model. It provides the model with an understanding of the context of the conversation.

<!-- markdownlint-disable MD024 -->
##### Variables
<!-- markdownlint-enable MD024 -->

- `system_message_chat_conversation` (str): The system message for the chat conversation
- `query_prompt_template` (str): The query prompt for enhancing the search keywords for the knowledge base

<!-- markdownlint-disable MD024 -->
##### Example
<!-- markdownlint-enable MD024 -->

```python
system_message_chat_conversation = """You are an AI built by Deutsche Telekom. You have to answer the question abiding by the following rules:
- You will refer to yourself as the CCoE Assistant. You do not have a name.
- You are brief and precise in your response.
- Take only the information provided in the prompt into account for your answer.
- Each source has a name followed by a colon. You have always to include the source name in front of the colon for each fact you use in the response. Use square brackts to reference the source and list each source separately e.g. [info1.pdf][info2.pdf].
- In case of ambiguity questions by the human ask clarifying questions.
- Translate your answer into {promptlang}
- If there are nothing provided in the prompt say {noidea}.
{injected_prompt}
"""

query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about questions.
    Generate a search query based on the conversation and the new question.
    Do not include cited source filenames or numbers in brackets e.g. [1] or [3] and document names e.g info.txt or doc.pdf in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.
    If the question is not in {language}, translate the question to {language} before generating the search query.
"""
```

#### File: `ABBREV`

The abbreviations file is a csv file that contains the abbreviations the user may use in the chat conversation that the model should be aware of. This is especially useful for company-specific abbreviations or acronyms.

**Note**: You need to provide at least one abbreviation.

<!-- markdownlint-disable MD024 -->
##### Example
<!-- markdownlint-enable MD024 -->

```csv
CMS, Content Management System
DT, Deutsche Telekom
```

## Known Issues

- The OpenAI instance is not always correctly deployed. If you encounter issues, set the `AZURE_REDEPLOY_OPENAI` variable to `true` in the `ENVIRONMENT` file to redeploy the OpenAI instance.
- If the backend is not working after deployment, try accessing the `/docs` endpoint to see if the backend is running. If it is not, try restarting or bumping the App Service Tier.
- If the frontend is returning unexpected errors, go to the network tab in the browser developer tools and check the response of the API calls. This will give you more information about the error.
- If the search is returning an error, set one setting in the semantic ranker. This is a known bug in microsofts deployment.
