<!-- markdownlint-disable MD033 -->

# <span>Mate as a Service by CCOE DTIT</span>

<!-- markdownlint-enable MD033 -->

> :warning: **PIPELINE STUCK issue** :warning:
>
> The newest update contains a new default runner, to fix old versions, just set the variable `DEFAULT_RUNNER` to
> `otc_run_sysbox_m` or another new one.

---

> :warning: **CHANGELOG.md** :warning:
>
> You can now find the latest changes in the
> [CHANGELOG.md](https://gitlab.devops.telekom.de/red-october/azure-search-openai-backend/-/blob/main/CHANGELOG.md)
> file. In case of any issues after updating, first check the changelog for breaking changes or new features. It is your
> responsibility to keep up with the changes in the project.

- [What is Mate?](#what-is-mate)

## What Is Mate?

Mate (formerly known as T-Chat) is a service that enables users to ask questions and get answers from a large knowledge
base. The knowledge base is built from various sources like PDFs, websites, and wikis. The service is built on top of
Azure services like Azure Cognitive Services, Azure Blob Storage, and Azure OpenAI. The service is designed to be used
by employees to get answers to their questions quickly and efficiently.

The Mate application is PSA approved, that means you can reference our PSA in your own PSA. The only thing you need to
clarify is the data you want to use. Furthermore, each user must obtain separate approval from the Group Workers Council
(KBR) before the data can be used in production. If you want to use this software for production, please reach out to
[Jerome Chevaillier](https://gitlab.devops.telekom.de/red-october/azure-search-openai-backend/-/blob/main/mailto:Jerome.Chevaillier@telekom.de)
for preparation.

This repository was initially inspired by the
[Microsoft Azure Sample Repository](https://github.com/Azure-Samples/azure-search-openai-demo/tree/main).




