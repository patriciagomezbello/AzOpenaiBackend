# LangChain Integration<!-- omit in toc -->

The LangChain integration allows you to load data from different sources into Mate. A list of our supported langchain data integrations can be found in [here](./README.md).

These can be extended with [other document loaders](https://python.langchain.com/docs/integrations/providers/) as needed.

- [Available Variables](#available-variables)
  - [`LC_MODE`](#lc_mode)
  - [`LANGCHAIN_CONFIG`](#langchain_config)
    - [Values](#values)
      - [`loader` - Mandatory](#loader---mandatory)
      - [`config` - Mandatory](#config---mandatory)
      - [`splitter` - Optional](#splitter---optional)
      - [`category` - Optional](#category---optional)
    - [Example](#example)

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

##### `loader` - Mandatory

Defines which loader you want to use. The following loaders are available:

- `confluence`: Load data from Confluence.
- `docusaurus`: Load data from Docusaurus.
- `rurl`: Load data from a URL.

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

##### `splitter` - Optional

The splitter to use. The following splitters are available:

- `standard` (default): Use the standard splitter. (Microsoft splitting)
- `recursive`: Use the recursive splitter. (LangChain splitting)

##### `category` - Optional

The category of the data source. This is used to group the data sources in the frontend.

If you don't want to use a category, you need to delete the `category` key from the configuration.

#### Example

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
]
```
