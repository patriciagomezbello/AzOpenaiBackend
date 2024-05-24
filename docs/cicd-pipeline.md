# CI/CD Pipeline<!-- omit in toc -->

This page provides information on the CI/CD pipeline for Mate. The pipeline is responsible for multiple tasks, such as deploying the infrastructure, deploying the backend, syncing the storage data, and more.

- [Prequisites](#prequisites)
- [Pipeline Overview](#pipeline-overview)
- [Jobs](#jobs)
  - [`all-start` Job](#all-start-job)
  - [`app-start` Job](#app-start-job)
  - [`data-start` Job](#data-start-job)
  - [`jira-bot-start` Job](#jira-bot-start-job)

## Prequisites

You will need to have a private GitLab Runner for CI/CD pipeline. You can find our GitLab Runner package [here](https://gitlab.devops.telekom.de/red-october/public/azure-gitlab-runner-private).

The pipeline automatically starts and stops the GitLab Runner based on the pipeline activity.

**Note:** Please also have a look at the automatic shutdown times, to prevent too many costs, in case of pipeline failures.

## Pipeline Overview

The CI/CD pipeline for Mate consists of multiple jobs. Some of the jobs are triggered automatically, while others are triggered manually.

You may only care about the jobs that are triggered manually, as they are the ones you will interact with.

The jobs that are triggered automatically are mainly for development purposes.

## Jobs

### `all-start` Job

_tbd_

### `app-start` Job

_tbd_

### `data-start` Job

_tbd_

### `jira-bot-start` Job

_tbd_