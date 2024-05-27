# Mate Documentation<!-- omit in toc -->

Welcome to the Mate documentation! This documentation provides information on how to deploy and use Mate, a service that enables users to ask questions and get answers from a provided knowledge base. The service is built on top of Azure services like Azure AI Search, Azure Blob Storage, and Azure OpenAI. The service is designed to be used by Telekom employees to get answers to their questions quickly and efficiently.

- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Data Integration](#data-integration)
- [Jira Ticket Bot](#jira-ticket-bot)
- [TARDIS Integration](#tardis-integration)
- [Development](#development)

## Prerequisites

Before using your own instance of Mate, you need to have the following prerequisites:

- **A subscription on the DTIT Azure Tenant (no sandbox allowed)**
- **Contributor access to the Azure Subscription** for the service principal
- **A resource group in the subscription named `rg-<AZURE_ENV_NAME>`** (e.g. `rg-mate`)
- **A private GitLab Runner for CI/CD**:
  - You can find our GitLab Runner package [here](https://gitlab.devops.telekom.de/red-october/public/azure-gitlab-runner-private)
  - You need to create two subnets in your existing VNet (`vnet_dtit_cix00xx` of your subscription):
    1. One with the prefix `/27` (e.g. `sn-mate`)
    2. The other with at least `/28` (e.g. `sn-mate-appservice`)

## Deployment

To deploy Mate, follow the instructions in the [deployment guide](./deployment.md).

## Data Integration

To integrate your data into Mate, follow the instructions in the [data integration guide](./data-integration/README.md).

## Jira Ticket Bot

You can use the Jira Ticket Bot to answer your Jira Service Desk tickets with the help of Mate. To learn more about the Jira Ticket Bot, please refer to the [Jira Ticket Bot](./jira-ticket-bot.md) documentation.

## TARDIS Integration

You can integrate the Mate API into TARDIS. To see an example of how to integrate an API running on Azure into TARDIS, you can refer to our [example repository](https://gitlab.devops.telekom.de/red-october/public/azure-tardis-spacegate-integration).

## Development

To contribute to Mate, follow the instructions in the [development guide](./dev/README.md).
