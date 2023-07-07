## <span style="color: #e20074">T-Chat as a Service </span>
- ChatGPT + Telekom data with Azure OpenAI and Cognitive Search

- Currently in development state, no final branch or feature structure yet
- forked from Microsoft Azure Sample Repository (https://github.com/Azure-Samples/azure-search-openai-demo/tree/main) and adjusted (by using the vector branch, adding logs, extracting prompt and cleaning up unnecessary components)

## How to run and use locally?

this works in bash and powershell, required are Python 3.10 or higher, azd and az cli

login 

``` bash
# login with azd and az cli's
azd auth login
az login #required currently for getting access to services
```

deploy/update everything 


``` bash
# bundles backend, deploys infrastructure and 
# deploys backend to app service 
azd up 
```


##### Pending TODO:
- update infrastructure from MS Repository, as OpenAI will currently trigger errors for ```azd up```and ```azd provision```

deploy application code

``` bash
# deploys backend to app service 
azd deploy
```

start python server locally (for development)

``` bash
# navigate to the repository folder
appscripts/start.sh
```
with pwsh

``` powershell
# navigate to the repository folder
./appscripts/start.ps1
```

update data locally (will update real search service)

- this will synchronise the local/repository data with a storage account and act depending on if it is new (will be uploaded and processed), only in the storage account (will be deleted from storage and search), or changed (will be updated in storage and search)
- the comparison is done via using md5 hashes, which is a mitigated security issue in gitlab, as we do not use it for encryption, but comparison.

``` bash
# navigate to the repository folder
scripts/prepdocs.sh
```
with pwsh

``` powershell
# navigate to the repository folder
./scripts/prepdocs.ps1
```

##### testing the api without UI (localhost:5000/chat or 127.0.0.1:5000/chat)

- example json with overrides and chat message for using as json body against api

```json
{
	"history": [
		{
			"user": "what do I need to do to get an Azure Subscription?"
		}
	],
	"approach": "rrr",
	"overrides": {
		"semantic_ranker": true,
		"semantic_captions": false,
		"top": 3,
		"temperature": 0.3,
		"retrieval_mode": "hybrid",
		"languague": "en-US"
	}
}
```

##### using with localhost based UI

- [Clone or Download UI Repository](https://gitlab.devops.telekom.de/red-october/telit-azure-openai-gpt-frontend)
- Prerequisites: 
    - nodejs must be installed
    - SERVER_ENVIRONMENT in .env in .azure needs to be "local" to disable cors issues

- configure .env for local usage

``` bash
# put these 3 lines in .env or ask someone from the team to send you one
VITE_MODEL_CONFIG={"local": {"enc":"gpt-3.5-turbo-0301","ctoken": 4097,"url": "http://127.0.0.1:5000", "type":"custom", "apiId": "placeholder"}}
VITE_MSAL_CLIENT_ID=client_id for local login and auth against (TODO: allow auth disabling for local usage)
VITE_MSAL_TENANT_ID=https://login.microsoftonline.com/TENANT_ID
```

``` bash
# navigate into UI repository
# install all dependencies
npm i 

# start development server on localhost:5173
npm run dev
```

# Pipeline and Repository structure?

Pipeline is splitted into different approaches currently
##### Pending TODO: 
- find final solution for using infrastructure and code deployment clean (MS consultant can help here), .env must be excluded if relevant data like appinsights con string will be inside

- current status: 3 steps, one for deploying everything, one for infrastructure and one for data update

Repository currently uses several branches in maybe? bad practice

- main branch is most uptodate and represents one (and the main) environment
- instance 2 for example is another environment, the deployment there would trigger another resource group

##### Pending TODO:
 - same issue, we need a nice working solution for gitlab to manage different environments clean and nice with azd, using full and partial deployment of infrastructure or code or data only. Also the .env needs to be integrated smoothly, maybe we even will use more than one.


