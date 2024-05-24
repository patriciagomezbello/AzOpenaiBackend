# CI/CD Variables<!-- omit in toc -->

In general, there are several CI/CD variables, that enable different settings for the data loading process.

Because of backwards compatibility, all of these variables are optional. However, it is recommended to set them to ensure a smooth data loading process.

- [Data Integration Variables](#data-integration-variables)
- [File Integration Variables](#file-integration-variables)
  - [Git Mode](#git-mode)
  - [Blob Mode](#blob-mode)
    - [Required steps](#required-steps)
    - [File Structure](#file-structure)
- [LangChain Integration Variables](#langchain-integration-variables)

## Data Integration Variables

The following variables are available:

- `DATA_MODE`: The mode of the data integration.
Available values are:
  - `file` (default): Load only file data sources.
  - `all`: Load all data sources.
  - `lc`: Load only LangChain data sources.
- `DATA_CONVERT`: If set to `true`, data from the `data2convert` folder for the [file integration](#file-integration-variables) will be converted and put into the `data` folder during data integration.

## File Integration Variables

- `FILE_MODE`: This allows you to use Azure Storage Blobs directly for the data integration. Available values are:
  - `git` (default): Load the data from the Git repository.
  - `blob`: Load the data from Azure Storage Blobs.

### Git Mode

In order to connect your file data (PDFs) to your Mate instance, a second git repository is required. This repository needs to have all `.pdf` files in the `data` directory.

To enable a permanent connection between both repositories, a connection between the two repositories is required. The data repository must allow the Mate repository to access its data with the [`CI_JOB_TOKEN`](https://docs.gitlab.com/ee/ci/variables/predefined_variables.html#variables-reference) variable.

Here is how you can set up the connection:

- Step 1: Go to Settings and CI/CD -> Token Access
  ![DATA_ACCESS_1](/docs/img/DATA_ACCESS_1.png)

- Step 2: Put in your data (group or personal name / project name)
  ![DATA_ACCESS_2](/docs/img/DATA_ACCESS_2.png)

- Step 3: Check if it has been added
  ![DATA_ACCESS_3](/docs/img/DATA_ACCESS_3.png)

### Blob Mode

In order to connect your data from another directory in your storage account, you will need a policy exemption on your storage account. Therefore, please create a [ticket](https://jira.telekom.de/servicedesk/customer/portal/301/group/906).

The exemption will allow you to put your IP address into the storage account networking settings, to be able to connect and upload data in the private setup.

#### Required steps

- Exemption request
- IP address under Networking
- Create container `data`
- Upload your files

#### File Structure

Only one level of directories is allowed, so the files either need to be in the root of the container or in a direct subfolder. e.g. `data/` or `data/subfolder/` are allowed, but `data/subfolder/subfolder/` is not.

Directories must not contain any underscores (`_`) or special characters, as this will break the data loading process.

## LangChain Integration Variables

For more information on the LangChain integration, refer to the [LangChain Integration](langchain.md) page.
