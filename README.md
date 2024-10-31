<!-- markdownlint-disable MD033 -->
# <span style="color: #e20074">Mate as a Service by CCOE DTIT</span><!-- omit from toc -->
<!-- markdownlint-enable MD033 -->

> :warning: **PIPELINE STUCK issue** :warning:
>
> The newest update contains a new default runner, to fix old versions, just set the variable `DEFAULT_RUNNER` to `otc_run_sysbox_m` or another new one.

---

> :warning: **CHANGELOG.md** :warning:
>
> You can now find the latest changes in the [CHANGELOG.md](./CHANGELOG.md) file.
> In case of any issues after updating, first check the changelog for breaking changes or new features.
> It is your responsibility to keep up with the changes in the project.

- [What is Mate?](#what-is-mate)
- [Documentation](#documentation)
  - [Deployment](#deployment)
  - [Data Integration](#data-integration)
- [Roadmap and Information](#roadmap-and-information)
- [Contributing](#contributing)
- [License](#license)

## What is Mate?

Mate (formerly known as T-Chat) is a service that enables users to ask questions and get answers from a large knowledge base. The knowledge base is built from various sources like PDFs, websites, and wikis. The service is built on top of Azure services like Azure Cognitive Services, Azure Blob Storage, and Azure OpenAI. The service is designed to be used by employees to get answers to their questions quickly and efficiently.

The Mate application is PSA approved, that means you can reference our PSA in your own PSA. The only thing you need to clarify is the data you want to use. Furthermore, each user must obtain separate approval from the Group Workers Council (KBR) before the data can be used in production. If you want to use this software for production, please reach out to [Jerome Chevaillier](mailto:Jerome.Chevaillier@telekom.de) for preparation.

This repository was initially inspired by the [Microsoft Azure Sample Repository](https://github.com/Azure-Samples/azure-search-openai-demo/tree/main).

## Documentation

You can find the documentation with deployment instructions, data integration, and more in the [docs](./docs/README.md) directory of this repository.

### Deployment

To deploy Mate, you can follow the instructions in the [deployment guide](./docs/deployment.md).

### Data Integration

To integrate your data into Mate, you can follow the instructions in the [data integration guide](./docs/data-integration/README.md).

## Roadmap and Information

You can find the roadmap and more information about the project on our [YAM page](https://yam-united.telekom.com/pages/azure-dtit-cloud/apps/content/mate).

## Contributing

If you want to contribute to Mate or get a local copy running, please follow the instructions in the [contributing guide](./CONTRIBUTING.md).

You can learn more about the project structure and how to get started in the [development guide](./docs/dev/README.md).

## License

The code in this repository is licensed under a dual license. You can find more information in the [LICENSE](/LICENSE) file.
