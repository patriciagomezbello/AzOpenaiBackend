# Data Integration<!-- omit in toc -->

You can integrate data from different sources into Mate. You can follow the steps below to integrate your data.

**Note: The data integration must be done by someone that is proficient with GitLab CI/CD and fully understands its concepts and functionalities.**

- [What data can be integrated?](#what-data-can-be-integrated)
  - [Why only these data formats?](#why-only-these-data-formats)
- [Data Integration Pipeline](#data-integration-pipeline)
  - [CI/CD Variables](#cicd-variables)
  - [LangChain Integration](#langchain-integration)

## What data can be integrated?

Mate supports the following data formats:

- PDF files
- [LangChain Integration](https://python.langchain.com/docs/modules/data_connection/), currently we have document loaders for the following data sources:
  - [Confluence / MyWiki](https://www.atlassian.com/software/confluence)
  - [Docusaurus](https://docusaurus.io/)
  - URLs/Websites
  - Can be extended with [other document loaders](https://python.langchain.com/docs/integrations/providers/) as needed

### Why only these data formats?

We value interpretability and transparency for our users. Therefore we always want to integrate a way to show access sources to the end user.

**Note:** The integration of sources that are not accessible or showable like databases, or other internal systems, is currently not planned.

## Data Integration Pipeline

This repository contains the data integration pipeline for Mate. The pipeline is responsible for loading data into the Mate knowledge base.

For more information on our CI/CD pipeline, see the [CI/CD Pipeline](/docs/cicd-pipeline.md) page.

### CI/CD Variables

For more information on the available CI/CD variables for the data loading process, see the [CI/CD Variables](cicd-variables.md) page.

### LangChain Integration

For more information on the LangChain integration, see the [LangChain Integration](langchain.md) page.
