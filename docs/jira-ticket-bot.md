# Mate Jira AI Bot Overview

The Mate Jira AI Bot automatically answers customer requests in JIra tickets automatically.

The main function of the ticket handling bot processes issues from Jira. It begins by fetching the details of each issue
based on a predetermined query. For each issue, it checks if there is a last comment and combines this with the issue's
description to form the input for an AI tool.

This input is then summarized using AI technology, which is used for categorizing the issue. The bot then labels the
input based on predefined prompts. These labels are then matched with a list of categories to filter the responses from
the AI tool.

If the issue's category is either predefined or part of a list of excluded categories, the bot skips the issue, reducing
the number of calls to the AI model. If not, the issue is sent to the AI tool's chat API to generate a response.

The bot then evaluates the response for its helpfulness. If the response is not helpful, the bot checks if more detailed
input is needed from the user. Depending on this check, the bot either asks the user for more information or escalates
the issue to a human agent.

Finally, the bot processes any additional data points in the AI tool's response, attaches any relevant documents or
links to the issue, adds a comment with the prepared response, and moves the issue to the next stage in the workflow.

## How Does the Mate Jira AI Bot Work in More Detail?

The main function in `ticketBot.py` is responsible for processing Jira issues. It iterates over each issue and performs
the following steps:

1. It retrieves the attributes of the issue according to the JQL Query (Jira Query Language) given in variable
   `JIRA_JQL`.
2. If the issue has a last comment, it concatenates the last comment and the description of the issue to form the input
   for Mate. If the issue does not have a last comment, it uses the description of the issue as an input for Mate. If
   the variable `JIRA_CATEGORIZATION_FIELD` is set, the categorization from Jira is added to the description.
3. It uses Azure OpenAI's ChatCompletion API to summarize the issue (the summarized text is used for categorization and
   provide in the ticket response what the AI bot understood).
4. If there are system prompts in `OPENAI_CATEGORIZE_MESSAGES` the input for Mate (the description and last comment of
   the issue) is labeled according to the given prompts. The first label given by the first system prompt in the
   variable will be used to set the label as a filter for the Mate RAG instance (if filters are used!) to constrain the
   search results to documents under this category. Because labels produced for the Mate input can be different from the
   filter names, you need to map possible labels to the filter name in the variable
   `MATE_CATEGORY_FILTER_TO_PROMPT_LABELS`. Example: you ask to label the request if it belongs to a "Google" topic and
   the filter is named "GCP" in the Mate RAG instance, then you can map the label "Google" to the category filter "GCP"
   in the variable like this: `{"GCP":["Google"]}`. This is important, because here you can also put every name that
   ticket writers are using to reference the environment. If the variable `OPENAI_CATEGORIZE_MESSAGES` is empty no
   categorization takes place, filters in Mate RAG cannot be used and issues cannot be skipped. You can define
   indefinite number of prompt messages.
5. If the categorization of the issue is not None or the category is in the list defined by the variable
   `EXCLUDED_CATEGORIES`, the issue will be skipped to from answering, reducing the amount of LLM calls (GreenIT
   Feature; e.g. is a specific kind of order, that needs a human agent to do it).
6. If the categorization is None or the category is not in the list defined by the variable `EXCLUDED_CATEGORIES`, the
   issue input will be sen to the chat API of the Mate RAG instance to get an answer. If a filter is defined in step 4,
   the overrides object to constrain the search in the vector database to the corresponding sections is not None in the
   /chat API call.
7. The response will subsequently evaluated if the answer was helpful, by providing the issue input and the answer to
   the LLM model, with the request if he thinks that he could help or not. This feature prohibits that "I don't know"
   answers are given back to the issue creator (customer).
8. If he was unable to assist with the answer, he will call the LLM model again to check if the creator has delivered
   enough detailed input to answer his question. If yes, the customer will be asked for more information in the issue
   and the issue will be changed into the state given in variable `JIRA_TRANSITION_NAME`. This raises the chance to
   solve the ticket automatically with more detailed content (if it is delivered). If no, the ticket will be transferred
   to a human agent by transition the state to the state in variable `JIRA_TRANSITION_NAME_IF_UNABLE_TO_ASSIST`
9. It then processes the data points in the Mate response. If a data point is a PDF, it adds the document name and page
   number to the sources and attaches the pdf file to the issue. If a data point is a URL, it adds the URL to the
   sources. In addition the function adds a comment to the issue in Jira with the prepared response and transitions the
   issue to the next state in the workflow according to variable `JIRA_TRANSITION_NAME`.

The function uses the `JiraClient` to interact with Jira and the `OpenAIClient` to interact with OpenAI. It also uses
the `MateClient` to interact with Mate.

## Simulation Mode

The Mate Jira AI Bot is simulating the processing by default. This can be used to evaluate how changes made in the
configuration below are affecting the quality of the answers. Highly recommended to use it, because otherwise the
customer may get unsatisfying answers.

## Debugging

You can set the variable `DEBUG_MODE`to `True` to see in the log each and every step to understand how an answer to an
customer request in a Jira issue is created by Mate Jira AI Bot.

## Configuration

### Prepare Authentication for the Mate RAG API

You need a separate service principal (The client id will be the value of `JIRA_MATE_SP_CLIENT_ID`) to call the Mate RAG
API, in the same entra id tenant where the Mate RAG backend is using the app registration for authentication and
authorization. The client id of this app registration can be found in variable `AZURE_AUTH_CLIENT` of the `ENIVRONMENT`
variable and the entra id in the variable `AZURE_TENANT_ID`. On the app registration in variable `AZURE_AUTH_CLIENT` you
need to expose an API. The APP Role where access to should be granted in this app registration must be accessible by
Admin + Users + Applications! The separate service principal for Mate Jira AI Bot must the be granted the access to the
exposed API with the corresponding app role.

### OpenAI Model for Categorization

To get the best results for the categorization of issues and the the answer use a at least a `GPT-4` model or newer. In
case the Mate RAG backend is using gpt3.5 model, deploy a GPT-4 model in addition.

### Environment Variables of Type "Variable"

| Variable                 | Description                                                                                                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `JIRA_MATE_SP_CLIENT_ID` | The client ID for the Jira Mate Service Principal.                                                                                                                                                                                  |
| `JIRA_MATE_SECRET`       | The secret key for the Jira Mate Service Principal                                                                                                                                                                                  |
| `JIRA_MATE_SCOPE`        | The scope for the Mate RAG API the Jira Mate Service Principal is using to get the answers. It is the combination of value in variable `AZURE_AUTH_CLIENT` and `/.default`. Example: `xxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx/.default` |
| `JIRA_SERVER`            | The URL of the Jira server. Example: `https://jira.telekom.de`. If this variable exists the pipeline for the Mate Jira bot appears                                                                                                  |
| `JIRA_USERNAME`          | The username of the technical user used to log into Jira.                                                                                                                                                                           |
| `JIRA_TOKEN`             | The token used to authenticate with Jira for the technical user                                                                                                                                                                     |
| `DEBUG_MODE`             | `True` or `False` - prints each and every step and result to the log                                                                                                                                                                |

The variables `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` and `AZURE_TENANT_ID` are mandatory but should be already
configured for the Mate RAG backend.

### Environment Variables of Type "File"

| Variable                                   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `JIRA_TRANSITION_NAME`                     | The name of the default transition in Jira, that should be used for a successful answer and if the Mate Jira AI Bot is able to assist. E.g. `"Respond to customer"`                                                                                                                                                                                                                                                                              |
| `JIRA_TRANSITION_NAME_IF_UNABLE_TO_ASSIST` | The name of the transition in Jira if the bot is unable to assist. E.g. `"Transfer to human agent"`                                                                                                                                                                                                                                                                                                                                              |
| `JIRA_JQL`                                 | The JQL (Jira Query Language) used to find issues in Jira. Example: `"project = 'SDCCOE' AND assignee IS EMPTY and status = 'Waiting for support'"`                                                                                                                                                                                                                                                                                              |
| `JIRA_CATEGORIZATION_FIELD`                | The field in Jira used for categorization. Example: `"fields.customfield_18129.requestType.name"`                                                                                                                                                                                                                                                                                                                                                |
| `JIRA_MESSAGE_TEXT`                        | The message text in the footer of the answer, that informs the customer that an AI has answered this issue. Example: `"This answer is generated by AI - if you are satisfied please close the ticket. If not, please provide more details. If you are still not satisfied, please put it into state: "`. The state will be added from the content of variable `JIRA_TRANSITION_NAME_IF_UNABLE_TO_ASSIST`                                         |
| `OPENAI_CATEGORIZE_MESSAGES`               | The messages used by OpenAI to categorize the customer request in the Jira issue. It is list object. Example: `'["You help to categorize the text from users according to the following rule: provide only one label from the following categories:\AWS \n Azure \n Google \n Mate \n Others","You help to categorize the text from users according to the following rule: provide a label from the following categories:\nOrder \n Question"]'` |
| `EXCLUDED_CATEGORIES`                      | The categories that are excluded from categorization. Example: `'["Azure_Order","AWS_Order"]'`                                                                                                                                                                                                                                                                                                                                                   |
| `MATE_CATEGORY_FILTER_TO_PROMPT_LABELS`    | The labels used by the Mate client for categorization. This is a dictionary with key-list-pairs. Example: `'{"AWS":["AWS","aws"],"Azure":["Azure", "Mate","azure","Azure-Firewall"],"GCP":["GCP","gcp","Google"],"Others":[],"CaaS":["CaaS"]}'`                                                                                                                                                                                                  |
| `OPENAI_MODEL`                             | The deployment name of the model used for categorization and evaluation in Azure openai Resource (see variable `AZURE_OPENAI_SERVICE`) Should be a at least a GPT-4 model.                                                                                                                                                                                                                                                                       |
| `SIMULATE`                                 | A flag indicating whether to simulate actions or perform them for real. If you do not specify it, the default is `True`. For productive usage you have to set the value to `False`                                                                                                                                                                                                                                                               |

The variables `BACKEND_URI` and `AZURE_OPENAI_SERVICE` are mandatory but should be already configured for the Mate RAG
backend.

## Schedule a Regular Task in Your GIT Repository

A regular task can be scheduled in GIT for the pipeline. Please specify for the Mate Jira AI Bot the variable
`SCHEDULED_TASK` with the value `JiraTicketBot`, so that only the Mate Jira Ai Bot will be executed on that schedule!

## Technical Description

### Python Class Descriptions

#### JiraClient Class Functions

- `__init__(self, server, username, token)`: Initializes the JiraClient with server, username, and token.

- `authenticate_jira(self)`: Authenticates with the Jira server.

- `read_ticket(self, ticket_id)`: Reads the details of a specific Jira ticket.

- `get_issues(self, jql_str)`: Executes a JQL query and returns the resulting issues.

- `get_default_status_ids(self, status_name)`: Searches for a specific default status and returns its ID.

- `get_transitions(self, issue_id)`: Retrieves the transitions for a specific issue.

- `get_transition_id(self, transitions, transition_name)`: Retrieves a specific transition from the provided JSON
  object.

- `transition_issue(self, issue_id, transition_id)`: Transitions an issue to a new state.

- `add_comment(self, issue_id, comment)`: Adds a comment to an issue.

- `get_last_comment(self, issue_id)`: Retrieves the last comment from an issue.

- `attach_file(self, issue_id, file_path)`: Attaches a file to an issue.

- `read_attachment(self, issue_id, attachment_id)`: Downloads and reads an attachment from an issue.

### MateClient Class Functions

- `__init__(self, tenant_id, jira_mate_client_id, jira_mate_client_secret, scope, mate_backend_url)`: Initializes the
  MateClient with tenant_id, jira_mate_client_id, jira_mate_client_secret, scope, and mate_backend_url.

- `get_token(self)`: Tries to acquire a token silently. If no suitable token exists in cache, it gets a new one from
  Azure AD.

### OpenAIClient Class Functions

- `__init__(self, model, api_version, azure_openai_service)`: Initializes the OpenAIClient with the model, API version,
  and Azure OpenAI service. It sets up the OpenAI client with the necessary credentials and token provider.

- `chat_completion(self, system_message, message_text, openai_max_message_length=1000)`: This function uses OpenAI's
  ChatCompletion API to categorize the content. It takes in a system message, a user message, and an optional maximum
  message length. It returns the categorized content generated by the ChatCompletion API.

### ticketBot.py Functions

- `categorize_content(system_messages, message_text, openai_max_message_length, openai_client)`: This asynchronous
  function categorizes the content of a message according to the system messages. It uses the OpenAI client to determine
  the category of the system messages and a filter for AI search.

- `str_to_bool(s)`: This function converts a string to a boolean. It returns `True` if the string is "True", `False` if
  the string is "False", and raises a `ValueError` otherwise.
