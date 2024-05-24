<!-- markdownlint-disable MD033 -->
# <span style="color: #e20074">Mate as a Service by CCOE DTIT</span><!-- omit from toc -->
<!-- markdownlint-enable MD033 -->

> :warning: **Important Notice** :warning:
>
> Upgrading your Mate by executing the `all_start` command after May 24, 2024, may result in answers without your integrated data. To prevent this, please initiate the `data_start` task beforehand. This will automatically migrate your data to the new index format. If you have already run the `all_start` command, you can solve any issues by running the `data_start` command afterwards.

- [What is Mate?](#what-is-mate)
- [Documentation](#documentation)
  - [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## What is Mate?

Mate (formerly known as T-Chat) is a service that enables users to ask questions and get answers from a large knowledge base. The knowledge base is built from various sources like PDFs, websites, and wikis. The service is built on top of Azure services like Azure Search, Azure Cognitive Search, and Azure OpenAI. The service is designed to be used by Telekom employees to get answers to their questions quickly and efficiently.

The Mate application is PSA-compliant, but without the data. The data needs to be approved by the group workers council (KBR) before it can be used in production, each user needs to get approval separately. If you want to use this software for production, please reach out to [Jerome Chevaillier](mailto:Jerome.Chevaillier@telekom.de) for preparation.

This repository was initially inspired by the [Microsoft Azure Sample Repository](https://github.com/Azure-Samples/azure-search-openai-demo/tree/main).

## Documentation

You can find the documentation with deployment instructions, data integration, and more in the [docs](./docs/README.md) directory of this repository.

### Deployment

To deploy Mate, you can follow the instructions in the [deployment guide](./docs/deployment.md).

## Roadmap

- [x] Role-based Access Control (May 2024)
- [x] Runner costsaving waiting on running jobs, multiple mate per group support (April 2024)
- [x] Mate Jira Integration (March 2024)
- [x] Direct File Blob Data Integration (Feburary 2024)
- [x] Standardized OpenID Connect Auth (February 2024)
- [x] Langchain Data Integration (January 2024)
- [x] Feedback and Application Insights (November 2023)
- [x] Language Support (October 2023)
- [x] Initial Release (October 2023)

## Contributing

If you want to contribute to Mate or get a local copy running, please follow the instructions in the [contributing guide](./CONTRIBUTING.md).

You can learn more about the project structure and how to get started in the [development guide](./docs/dev/README.md).

## License

The code in this repository is licensed under a dual license. You can find more information in the [LICENSE](/LICENSE) file.
