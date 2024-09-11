# CHANGELOG.md

This file includes all the changes made to the Mate as a Service project.

## 2.1.0 *(2024-09-11)*

**Features:**

- Add GET /content endpoint (v1) to retrieve indexed content
- Allow GPT4o-mini as a model for Mate
- Introduction of `CHANGELOG.md`

## **2.0.0** *(2024-09-09)*

**Features:**

- a clear v1 API and allows better versioning and programming in the future (refactored).
- Allow using existing resources of OpenAI, Document Intelligence and Search for Mate because of Subnet redeployment issues (contributed from community)

**Breaking changes:**

- `/docs`, `/redocs`, `/openapi.yaml` and `/openapi.json` are not reachable under /v1 routes anymore
- `/health` endpoint is now available. It returns a 200 OK status code if the service is healthy and running

## Previous versions

Have a look at the documentation for already existing features, if you have any questions, please create an issue in the repository.
  