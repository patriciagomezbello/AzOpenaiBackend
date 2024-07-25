# LangChain Integration<!-- omit in toc -->

The LangChain integration allows you to load data from different sources into Mate. A list of our supported langchain data integrations can be found in [here](./README.md).

These can be extended with [other document loaders](https://python.langchain.com/docs/integrations/providers/) as needed.

- [Available Variables](#available-variables)
  - [`LC_MODE`](#lc_mode)
  - [`LANGCHAIN_CONFIG`](#langchain_config)
    - [Values](#values)
      - [`loader` - Mandatory](#loader---mandatory)
      - [`splitter` - Optional](#splitter---optional)
      - [`category` - Optional](#category---optional)
      - [`config` - Mandatory](#config---mandatory)
    - [Examples of each loader](#examples-of-each-loader)

## Available Variables

The following variables are available for the LangChain integration:

### `LC_MODE`

The mode of the LangChain integration. Available values are:

- `create` (default): Create and update the index. This will also cleanup the old index.
- `delete`: Delete the indexed sections.

### `LANGCHAIN_CONFIG`

The configuration for the LangChain integration. The behavior of this variable depends on the mode set in the `LC_MODE` variable.

You need to set this as `file` variable.

#### Values

(for examples in json format for each loader, see [Examples of each loader](#examples-of-each-loader))

##### `loader` - Mandatory

Defines which loader you want to use. The following loaders are available:

- `confluence`: Load data from Confluence.
- `docusaurus`: Load data from Docusaurus.
- `rurl`: Load data from a URL.
- `magentainfos`: Load data from magentainfos.
- `staffbase`: Load data from Staffbase.

##### `splitter` - Optional

The splitter to use. The following splitters are available:

- `standard` (default): Use the standard splitter. (Microsoft splitting)
- `recursive`: Use the recursive splitter. (LangChain splitting)

##### `category` - Optional

The category of the data source. This is used to group the data sources in the frontend.

If you don't want to use a category, you need to delete the `category` key from the configuration.

##### `config` - Mandatory

The configuration for the loader that you have [chosen](#loader---mandatory).

**Confluence:**

- `url`: The base URL of the Confluence instance.
- `username`: The email address of the user.
- `token_ref`: The name of the variable where the API key of the user is stored. **Do not put the API key directly into the config.**
- `space_key`: The space key of the Confluence/Wiki space that you want to load.
- `include_att`: Whether to include attachments or not. This can cause issues with uncommon file types.
- `limit`: The number of pages to load.
- `max_pages`: The maximum number of pages to load.

**Docusaurus:**

- `url`: The base URL of the Docusaurus website.

**RURL:**

- `url`: The base URL of the website.
- `max_depth`: The maximum link recursion depth.

**Magentainfos:**

- `auth_url` (str): The URL used for authentication.
- `api_url` (str): The base URL for the API.
- `client_id` (str): The client ID for authentication.
- `secret_reference` (str): The environment variable name where the client secret is stored.
- `categories` (List[str]): A list of categories to filter the documents. Example: `["category1", "category2"]`.
- `document_list` (List[DocumentRequest]): A list of document requests.
- `publish_date` (PublishDate | None): The publish date filter for the documents. Can be `None`.
- `rows` (int | None): The number of rows to fetch. Can be `None`.
- `page` (int | None): The page number to fetch. Can be `None`.
- `type` (DocumentType | None): The type of documents to fetch. Can be `None`.

**Staffbase:**

- `url` (str): The base URL of the Staffbase instance.
- `api_key_reference` (str): A reference to the API key used for authentication.
- `channels` (List[str]): An array of channel IDs to fetch content from. Example: `[]` (empty array if no channels are specified).
- `news_pages` (List[str]): An array of news page IDs to fetch content from. Example: `[]` (empty array if no news pages are specified).
- `posts` (List[str]): An array of post IDs to fetch specific posts. Example: `[]` (empty array if no posts are specified).
- `publish_filter` (str): A filter to specify which posts to publish.
- `language` (str): The language code for the content. Possible values: `"de"` or `"en"`.

#### Examples of each loader

```json
[
  {
    "loader": "confluence",
    "category": "wiki",
    "splitter": "standard",
    "config": {
      "url": "url of confluence, (e.g wiki.telekom.de)",
      "username": "email of user",
      "token_ref": "name of variable where api_key of user is put",
      "space_key": "space from wiki/confluence",
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
      "url": "url of website built on docusaurus"
    }
  }
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
        },
      ],
      "publish_date": "2023-10-01",
      "rows": 10,
      "page": 1,
      "type": "type"
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
      "categories": [],
      "document_list": [
        {
          "id": "4711",
          "type": "type"
        },
        {
          "id": "4712",
          "type": "type"
        },
      ],
      "publish_date": null,
      "rows": null,
      "page": null,
      "type": null
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
  }
]
```
