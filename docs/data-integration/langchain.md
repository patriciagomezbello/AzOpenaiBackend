# LangChain Data Loader<!-- omit in toc -->

The LangChain Data Loader enables you to import data from various web sources into Mate. For a list of supported LangChain data integrations, refer to [this document](./README.md). You can also extend these integrations with [other document loaders](https://python.langchain.com/docs/integrations/providers/) as needed.  
It also possible to extend integration with [LlamaIndex readers](https://docs.llamaindex.ai/en/stable/api_reference/readers/).


## Table of Contents<!-- omit in toc -->

- [Available Variables](#available-variables)
  - [`LC_MODE`](#lc_mode)
  - [`LANGCHAIN_CONFIG`](#langchain_config)
    - [Configuration Options](#configuration-options)
      - [`loader` - Mandatory](#loader---mandatory)
      - [`category` - Optional](#category---optional)
      - [`config` - Mandatory](#config---mandatory)
    - [Loader Examples](#loader-examples)

## Available Variables

### `LC_MODE`

This variable sets the mode for the LangChain integration. The available options are:

- `create` (default): Creates and updates the index. It also cleans up the old index.
- `delete`: Deletes the indexed sections.

### `LANGCHAIN_CONFIG`

This variable configures the LangChain integration based on the mode set in `LC_MODE`. You must set this as a `file` variable.

#### Configuration Options

##### `loader` - Mandatory

Specifies the loader to use. The available options are:

- `confluence`: Loads data from Confluence.
- `docusaurus`: Loads data from Docusaurus.
- `rurl`: Loads data from a URL.
- `magentainfos`: Loads data from Magentainfos.
- `staffbase`: Loads data from Staffbase.
- `jira`: Loads data from Jira.

##### `category` - Optional

Groups the data source into a category for frontend organization. If you do not wish to use a category, remove the `category` key from the configuration.

##### `config` - Mandatory

Specifies the configuration settings for the selected loader. Below are the configurations for each loader:

**Confluence:**

- `url`: Base URL of the Confluence instance.
- `username`: User’s email address.
- `token_ref`: Variable name where the API key is stored. **Do not include the API key directly in the config.**
- `space_key`: Space key of the Confluence/Wiki space to load.
- `include_att`: Option to include attachments (Note: May cause issues with uncommon file types).
- `limit`: Number of pages to load.
- `max_pages`: Maximum number of pages to load.

**Docusaurus:**

- `url`: Base URL of the Docusaurus website.

**RURL:**

- `url`: Base URL of the website.
- `max_depth`: Maximum link recursion depth.

**Magentainfos:**

- `auth_url`: URL used for authentication.
- `api_url`: Base URL for the API.
- `client_id`: Client ID for authentication.
- `secret_reference`: Environment variable name where the client secret is stored.
- `categories`: List of categories to filter documents (e.g., `["category1", "category2"]`).
- `document_list`: List of document requests.
- `publish_date`: Publish date filter for documents (can be `null`).
- `rows`: Number of rows to fetch (can be `null`).
- `page`: Page number to fetch (can be `null`).
- `type`: Document type to fetch (can be `null`).

**Staffbase:**

- `url`: Base URL of the Staffbase instance.
- `api_key_reference`: Reference to the API key for authentication.
- `channels`: Array of channel IDs to fetch content from (e.g., `[]` for none).
- `news_pages`: Array of news page IDs to fetch content from (e.g., `[]` for none).
- `posts`: Array of post IDs to fetch specific posts (e.g., `[]` for none).
- `publish_filter`: Filter specifying which posts to publish.
- `language`: Language code for the content (`"de"` or `"en"`).

**Jira**
- `url`: Base URL of Jira instance
- `username`: User’s email address.
- `token_ref`: Variable name where the API key is stored. **Do not include the API key directly in the config.**
- `project_key`: Project key in Jira
  
#### Loader Examples

Below are example configurations for different loaders:

```json
[
  {
    "loader": "confluence",
    "category": "wiki",
    "splitter": "standard",
    "config": {
      "url": "url of confluence, (e.g., wiki.telekom.de)",
      "username": "user@example.com",
      "token_ref": "API_KEY_VARIABLE",
      "space_key": "space_key",
      "include_att": false,
      "limit": 10,
      "max_pages": 10
    }
  },
  {
    "loader": "rurl",
    "splitter": "standard",
    "config": {
      "url": "url of website",
      "max_depth": 3
    }
  },
  {
    "loader": "docusaurus",
    "splitter": "standard",
    "config": {
      "url": "url of Docusaurus site"
    }
  },
  {
    "loader": "magentainfos",
    "splitter": "standard",
    "config": {
      "auth_url": "https://example.com/auth",
      "api_url": "https://api.example.com",
      "client_id": "your-client-id",
      "secret_reference": "SECRET_ENV_VAR",
      "categories": ["category1", "category2"],
      "document_list": [
        {
          "id": "4711",
          "type": "type"
        },
        {
          "id": "4712",
          "type": "type"
        }
      ],
      "publish_date": "2023-10-01",
      "rows": 10,
      "page": 1,
      "type": "type"
    }
  },
  {
    "loader": "staffbase",
    "category": "mystaffbasedata",
    "splitter": "standard",
    "config": {
        "url": "https://myown.staffbase.com",
        "api_key_reference": "API_KEY",
        "channels": [],
        "news_pages": [],
        "posts": ["123", "456"],
        "publish_filter": "all",
        "language": "de"
    }
  },
    {
        "loader": "jira",
        "config": {
            "username": "user.name@example.com",
            "token_ref": "JIRA_API_TOKEN",
            "url": "https://jira.example.com",
            "project_key": "PROJECT_KEY"
        }
    }
]
```
