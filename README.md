## <span style="color: #e20074">T-Chat as a Service </span>
- ChatGPT + Telekom data with Azure OpenAI and Cognitive Search

- Currently in development state, no final branch or feature structure yet
- forked from Microsoft Azure Sample Repository (https://github.com/Azure-Samples/azure-search-openai-demo/tree/main) and adjusted (by using the vector branch, adding logs, extracting prompt and cleaning up unnecessary components)


## Current Structure

- */app/backend* contains the python backend app
	-  */approaches* contains the approaches (currently only one, but is extendable)
		* chatreadretrieveread.py contains the backend process for the /chat api
		* core/*.py contains functions that are used in the approaches (for logging, handling sources in responses etc.)
	- app.py contains the flask (async version = quart) code that exposes the /chat and /content/{path} api for potential frontends
	- context.py (is cicd variable) contains the context of the backend, that is given to chatgpt, how to act etc.
	- requirements.txt contains the python packages for the backend

## How to deploy: **Fork repository and adjust CI/CD Settings**

### General Information

- Service Principal for deployment needs *Contributor* and *Telit-AccessAdministrator* rights for subscription
- Access Token, as it is recommeneded to not make it valid for longer then a few weeks

### File Variables 

- Name: **ENVIRONMENT**
Environment for deployment, deployment variables
AUTH_CLIENT 		-> backend service principal client id
ENV_NAME 			-> name of the environment (can be named invidually, needs to be consistent after)
SUBSCRIPTION-ID 	-> id of subscription
LOCATION 			-> please choose westeurope, everything else will be denied by policy
```
AZURE_AUTH_ClIENT="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_ENV_NAME="azure-search-openai-dev-env-name"
AZURE_SUBSCRIPTION_ID="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_LOCATION="westeurope"
```
**Important**: This is a minimal setup, more variables can be put into this file to use more existing services

- Name: **CONTEXT**
- - Context for the model to have an adjusted frame for the questions and answers. Python File

- - system_message_chat_conversation -> system message for the model
- - query_prompt_template -> query prompt for using question to retrieve information

``` python

system_message_chat_conversation = """You are an AI built by Deutsche Telekom. You have to answer the question abiding by the following rules:
- You will refer to yourself as the Assistant. You do not have a name.
- You are brief and precise in your response.
- Take only the information provided in the prompt into account for your answer.
- Each source has a name followed by a colon. You have always to include the source name in front of the colon for each fact you use in the response. Use square brackts to reference the source and list each source separately e.g. [info1.pdf][info2.pdf].
- In case of ambiguity questions by the human ask clarifying questions.
- If there are nothing provided in the prompt say {noidea}.
{injected_prompt}
"""

query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about questions.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames or numbers in brackets e.g. [1] or [3] and document names e.g info.txt or doc.pdf in the search query terms.
    If the question is not in English, translate the question to English before generating the search query.
    If the question is not in {language}, translate the question to {language} before generating the search query.
"""

```

### Environment Variables (not stored as file, but as variable)

- **OpenAILocation** 		-> *francecentral* or *westeurope* are supported
- **REPO_URL** 				-> gitlab repository url for the data (https://gitlab.devops.telekom.de/red-october/ccoe-data)
- **AZURE_CLIENT_ID** 		-> service principal id (sp for deployment)
- **AZURE_CLIENT_SECRET** 	-> secret for the service principal
- **AZURE_TENANT_ID**		-> tenant id (628242bd-7e70-4aa9-8ee1-72586b4540fe for our use cases)
- **ACCESS_TOKEN**			-> for api access, can be created under settings/accesstoken -> api, maintainer and up to 3 months validity



## How to run and use locally?

- this works in bash shell, required are Python 3.10 or higher, azd and az cli

### login 

``` bash
# login with azd and az cli's (pipeline client and local client need to be similar)
az login --service-principal -u AZURE_CLIENT_ID -p AZURE_CLIENT_SECRET --tenant AZURE_TENANT_ID
azd auth login --client-id AZURE_CLIENT_ID --client-secret AZURE_CLIENT_SECRET --tenant-id AZURE_TENANT_ID
```

### create required directories files that are in .gitignore

- .azure/
- .azure/config.json -> 
```json 
{
	"version":1,
	"defaultEnvironment":"<AZURE_ENV_NAME>"
}
```
- .azure/<AZURE_ENV_NAME>/
- .azure/<AZURE_ENV_NAME>/.env -> include ENVIRONMENT
- .azure/<AZURE_ENV_NAME>/config.json ->
```json 
{
  "infra": {
    "parameters": {
      "openAiResourceGroupLocation": "<OpenAILocation>"
    }
  }
}
```
- app/backend/core/context.py -> put in CONTEXT

- data 			-> include pdfs
- data2convert 	-> include .md, .png and more (coming soon)

### deploy/update everything 

``` bash
# bundles backend, deploys infrastructure and 
# deploys backend to app service 
azd up 
```

### deploy infrastructure

``` bash
# deploys backend to app service 
azd provision
```

### deploy application code

``` bash
# deploys backend to app service 
azd deploy
```

start python server locally (for development)
**Important**: Only works on macos out of the box, in app.py the cors needs to be active, you have to adjust the platform for your environment

``` bash
# navigate to the repository folder
cd app
./start.sh
```

update data locally (will update real search service)

- this will synchronise the local/repository data with a storage account and act depending on if it is new (will be uploaded and processed), only in the storage account (will be deleted from storage and search), or changed (will be updated in storage and search)
- the comparison is done via using md5 hashes, which is a mitigated security issue in gitlab, as we do not use it for encryption, but comparison.

``` bash
# navigate to the repository folder
scripts/prepdocs.sh
```

### testing the api without UI (localhost:5000/chat or 127.0.0.1:5000/chat)


##### using with localhost based UI

- [Clone or Download UI Repository](https://gitlab.devops.telekom.de/red-october/telit-azure-openai-gpt-frontend)


