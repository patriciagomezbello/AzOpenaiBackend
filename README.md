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
	- abbrev.py (is cicd variable) contains generated abbreviations that LLMs cannot know
	- requirements.txt contains the python packages for the backend


**pages.json** in every directory will create name1.pdf, name2.pdf in directory

``` json
{
	"name1": "https://example.com",
	"name2": "https://example.de",	
}
```

## How to deploy: **Fork repository and adjust CI/CD Settings**

### General Information & Requirements

- Service Principal for deployment needs *Contributor* rights
- A private gitlab runner is required -> a package that automatically installs one is available [in this repository](https://gitlab.devops.telekom.de/red-october/public/azure-gitlab-runner-private)
- The resource group has to be created upfront and be named "rg-<AZURE_ENV_NAME>"
	- if the AZURE_ENV_NAME = mate, the resource group must be named = rg-mate
	- if it is not done like this, there will be issues with providing rbac rights during the deployment

There is a requirement to add an ACCESS_TOKEN to your project to enable automatic infrastructure updates (state)
- **Step 1**: go to settings in your gitlab project, then go on Access Tokens
![ACCESS_TOKEN_1](documentation/ACCESS_TOKEN_1.png)
- **Step 2**: create a new Access Token that has api-Access and maintainer rights
![ACCESS_TOKEN_2](documentation/ACCESS_TOKEN_2.png)
- **Step 3**: create the token and copy it out (needs to be added as a ci/cd variable named "ACCESS_TOKEN")
![ACCESS_TOKEN_3](documentation/ACCESS_TOKEN_3.png)


### Environment CI/CD Variables (not stored as file variables, but as variable)
| Variable | Description |
| -------- | -------- | 
| OpenAILocation		|  *francecentral*, *swedencentral* or *westeurope* are supported
| REPO_URL 				|  gitlab repository url for the data (https://gitlab.devops.telekom.de/red-october/ccoe-data)
| AZURE_CLIENT_ID 		|  service principal id (sp for deployment)
| AZURE_CLIENT_SECRET 	|  secret for the service principal
| AZURE_TENANT_ID		|  tenant id (628242bd-7e70-4aa9-8ee1-72586b4540fe for our use cases)
| ACCESS_TOKEN      	|  for api access, can be created under settings/accesstoken -> api, maintainer and up to 3 months validity
| RUNNER_NAME      		|  The name of the provisioned private gitlab runner in the same subscription
| RUNNER_RG     		|  The resource group name of the provisioned private gitlab runner in the same subscription
| RUNNER_TAG    		|  The tag of the provisioned private gitlab runner in the same subscription
| SUBSCRIPTION_ID  		|  The id of the subscription
| DEV_ENV				|  *true* or *false*, only set in Gitlab please!!! (will delete the secure variant and replace with public variant during pipeline)

_____

### File Variables 

- **ENVIRONMENT**

| Variable | Description |
| -------- | -------- | 
| AZURE_AUTH_CLIENT *					| Client ID of app registration used for auth  						|
| AZURE_ENV_NAME *						| name of the environment 											| 
| AZURE_SUBSCRIPTION_ID *				| id of subscription  												| 
| AZURE_TENANT_ID *						| id of the tenant   												| 
| AZURE_LOCATION *						| location should be westeurope										| 
| AZURE_VNET_RESOURCE_GROUP * 			| Name of the existing VNET resource group	    					| 
| AZURE_VNET_NAME *						| Name of the existing VNET											| 
| AZURE_SUBNET_NAME *					| Name of the existing Subnet inside the existing VNET				| 
| AZURE_SUBNET_NAME_APPSERVICE *		| Name of the existing Subnet inside the existing VNET  			| 
| AZURE_ALLOWED_CORS *					| List of allowed URLs for cors  									| 
| AZURE_AUTH_ROLE   					| Name of the Role (not set = no authorisation, just authentication)|  
| AZURE_REDEPLOY_OPENAI   				| (re)deploys OpenAI Instance (for fixing current bug)  			|  
| AZURE_OPENAI_CHATGPT_MODEL_NAME   	| model name (gpt-35-turbo, gpt-35-turbo-16k, gpt-4, gpt-4-32k)   	| 
| AZURE_OPENAI_CHATGPT_MODEL_VERSION   	| model version (0613, 0914)   										| 
| AZURE_SEARCH_SERVICE_SKU  			| standard (basic,standard,standard2,standard3)						| 
| AZURE_APPSERVICE_SKU  				| B1 (B1,B2,B3,S1,S2,S3,P1,P2,P3,P4)  								| 

\* = **mandatory**

Example: 
```
AZURE_AUTH_ClIENT="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_ENV_NAME="azure-search-openai-dev-env-name"
AZURE_SUBSCRIPTION_ID="xxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
AZURE_TENANT_ID="628242bd-7e70-4aa9-8ee1-72586b4540fe"
AZURE_LOCATION="westeurope"
AZURE_VNET_RESOURCE_GROUP="rg-ci-vnet"
AZURE_VNET_NAME="vnet_dtit_cid00xx"
AZURE_SUBNET_NAME="sn-standard"
AZURE_SUBNET_NAME_APPSERVICE="sn-appservice"
AZURE_ALLOWED_CORS="http://localhost:1887,https://your.ui.url"

### optional parameters (shown with default values)

AZURE_REDEPLOY_OPENAI=true (after first deployment will be automatically false)
AZURE_OPENAI_CHATGPT_MODEL_NAME=gpt-35-turbo 
AZURE_OPENAI_CHATGPT_MODEL_VERSION=0613 

```
**Important**: This is a minimal setup, more variables can be put into this file to use more existing services
____

- **CONTEXT**
	- Context for the model to have an adjusted frame for the questions and answers. Python File
	- system_message_chat_conversation -> system message for the model
	- query_prompt_template -> query prompt for using question to retrieve information

``` python

system_message_chat_conversation = """You are an AI built by Deutsche Telekom. You have to answer the question abiding by the following rules:
- You will refer to yourself as the CCoE Assistant. You do not have a name.
- You are brief and precise in your response.
- Take only the information provided in the prompt into account for your answer.
- Each source has a name followed by a colon. You have always to include the source name in front of the colon for each fact you use in the response. Use square brackts to reference the source and list each source separately e.g. [info1.pdf][info2.pdf].
- In case of ambiguity questions by the human ask clarifying questions.
- Translate your answer into {promptlang}
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
____

- **ABBREV**
	- Abbreviations in csv format, will be transformed for better performance during each deployment
	- can be used to overwrite publicly known Abbreviations

``` csv
CMS, Content Management System
LLM, Large Learning Model
```

_____

### How to connect the data repository with your infrastructure and application?

In order to connect your file data (pdfs, mds etc.) to your backend, a second repository is required, that needs to have all pdf files in a folder named **data** and all other supported file formats in a folder named **data2convert**

To enable a permanent connection between those repositories, the follwing needs to be done:

- Step 1: Go to Settings and CI/CD -> Token Access
![DATA_ACCESS_1](documentation/DATA_ACCESS_1.png)

- Step 2: Put in your data (group or personal name / project name)
![DATA_ACCESS_2](documentation/DATA_ACCESS_2.png)

- Step 3: Check if it has been added
![DATA_ACCESS_3](documentation/DATA_ACCESS_3.png)

## How to use the pipeline:

- A private gitlab runner is required -> a package that automatically installs one is available [in this repository](https://gitlab.devops.telekom.de/red-october/public/azure-gitlab-runner-private), you can shut it down. The pipeline will automatically start and stop the runner if everything runs fine. Please also have a look at automatic shutdown times, to prevent to much costs.

- When you start a pipeline, nothing will be provisioned automatically

- If nothing is provisioned yet, you have to either execute the **all_start job** (provision + deploy) or the **provision_start** job

- If you want to update your infrastructure only, **provision_start**, if you want to update your application only, **deploy_start**

### How to run and use locally?

- this works in bash shell, required are Python 3.10 or higher, azd and az cli (only tested on mac os)

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


