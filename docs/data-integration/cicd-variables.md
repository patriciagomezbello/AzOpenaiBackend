# CI/CD Variables

In general, there are several CI/CD variables, that enable different settings for the data loading process.

Because of backwards compatibility, all of these variables are optional. However, it is recommended to set them to
ensure a smooth data loading process.

- [Data Integration Variables](#data-integration-variables)
- [File Integration Variables](#file-integration-variables)
  - [Git Mode](#git-mode)
  - [Blob Mode](#blob-mode)
    - [Required steps](#required-steps)
    - [File Structure](#file-structure)
- [LangChain Integration Variables](#langchain-integration-variables)

## Data Integration Variables

The following variables are available:

- `DATA_MODE`: The mode of the data integration. Available values are:
  - `file` (default): Load only file data sources.
  - `all`: Load all data sources.
  - `lc`: Load only LangChain data sources.
- `ROLE_CONFIG`: File Variable in json format. In this config, you can restrict categories to specific roles. Categories
  not defined in the `ROLE_CONFIG` will be flagged as `public`. Please be aware: If your model has only one role in
  `AZURE_AUTH_ROLE` defined, this variable is useless, as everyone has the same access in this case. It does not make
  sense to specify your "global" role (the role with the least access) any category assignment, just define categories
  that only a specific usergroup should have access in this file. The format is as follows:

  ```json
  {
    "category1": ["role_custom", "role_special"],
    "category2": ["role_special"]
  }
  ```

## File Integration Variables

- `FILE_MODE`: This allows you to use Azure Storage Blobs directly for the data integration. Available values are:
  - `git` (default): Load the data from the Git repository.
  - `blob`: Load the data from Azure Storage Blobs.
  - `all`: Load data from both Git and Azure Storage Blobs.


### Git Mode

In order to connect your file data (PDFs) to your Mate instance, a second git repository is required. This repository
needs to have all `.pdf` files in the `data` directory.

To enable a permanent connection between both repositories, a connection between the two repositories is required. The
data repository must allow the Mate repository to access its data with the
[`CI_JOB_TOKEN`](https://docs.gitlab.com/ee/ci/variables/predefined_variables.html#variables-reference) variable.

Here is how you can set up the connection:

- Step 1: Go to Settings and CI/CD -> Token Access

- Step 2: Put in your data (group or personal name / project name)

- Step 3: Check if it has been added

### Blob Mode

In order to connect your data from another directory in your storage account, you will need a policy exemption on your
storage account.

The exemption will allow you to put your IP address into the storage account networking settings, to be able to connect
and upload data in the private setup.

#### Required Steps

- Exemption request
- IP address under Networking
- Create container `data`
- Upload your files

#### File Structure

Only one level of directories is allowed, so the files either need to be in the root of the container or in a direct
subfolder. e.g. `data/` or `data/subfolder/` are allowed, but `data/subfolder/subfolder/` is not.

Directories must not contain any underscores (`_`) or special characters, as this will break the data loading process.

## LangChain Integration Variables

For more information on the LangChain integration ...
