import ast
import asyncio
import json
import logging
import os
import tempfile
from typing import List
from urllib.parse import quote

from jira import Issue

from .clients import JiraClient
from .clients import MateClient
from .clients import OpenAIClient


def str_to_bool(s: str) -> bool:
    match s.lower():
        case "true":
            return True
        case "false":
            return False
        case _:
            raise ValueError(f"{s} is not a valid boolean value")


# Geeting environment variables
jira_server = os.environ.get("JIRA_SERVER")
jira_username = os.environ.get("JIRA_USERNAME")
jira_token = os.environ.get("JIRA_TOKEN")
jira_jql = os.environ.get("JIRA_JQL")
jira_categorization_field = os.environ.get("JIRA_CATEGORIZATION_FIELD")
mate_label_system_messages: list[str] = ast.literal_eval(os.environ.get("OPENAI_CATEGORIZE_MESSAGES", "")) or []
azure_openai_service = os.environ.get("AZURE_OPENAI_SERVICE")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION") or "2023-09-15-preview"
model = os.environ.get("OPENAI_MODEL", "gpt-4o")
embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "embedding")
jira_mate_tenant_id = os.environ.get("AZURE_TENANT_ID")
jira_mate_sp_client_di = os.environ.get("JIRA_MATE_SP_CLIENT_ID")
jira_mate_secret = os.environ.get("JIRA_MATE_SECRET")
jira_mate_scope = os.environ.get("JIRA_MATE_SCOPE")
jira_transition_name = os.environ.get("JIRA_TRANSITION_NAME")
openai_max_message_length = int(os.environ.get("OPENAI_MAX_MESSAGE_LENGTH", "1000"))
jira_message_text = os.environ.get("JIRA_MESSAGE_TEXT")
excluded_categories = ast.literal_eval(os.environ.get("EXCLUDED_CATEGORIES", "")) or []
mate_filter_label_mapping = ast.literal_eval(os.environ.get("MATE_CATEGORY_FILTER_TO_PROMPT_LABELS", "")) or {}
jira_transition_name_if_unable_to_assist = os.environ.get("JIRA_TRANSITION_NAME_IF_UNABLE_TO_ASSIST", "")
mate_backend_url = os.environ.get("BACKEND_URI")
SIMULATE = str_to_bool(os.environ.get("SIMULATE", "true"))
DEBUG_MODE = bool(os.environ.get("DEBUG_MODE")) or False

if DEBUG_MODE:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def categorize_content(
    message_text: str, openai_client, system_messages: List[str] = [], openai_max_message_length: int = 1000
):
    """
    The categorize_content function is a custom function designed to categorize the content of a message
    according to the system messages.

    Input parameters:

    system_messages             : A list of system messages to be categorized. The default value is an empty list.
    message_text                : An optional parameter that contains the text of the message to be categorized.
                                  The default value is an empty string.
    openai_max_message_length   : An optional parameter that defines the maximum length of the
                                  message that is sent to OpenAI. The default value is 1000.

    Output parameters:

    ai_search_filter: A string that contains the filter for AI search. This value is determined based
                      on the responses from OpenAI for the first message.
    category        : A string that contains the category of the system messages. This value is determined
                      based on the responses from OpenAI.

    The function creates an OpenAIClient object and then iterates through each system message in
    system_messages. For each message, it calls the chat_completion method of the OpenAIClient to get a
    category response from OpenAI. This response is then added to the category variable. If it's the
    first message in the list, the response is also set as the ai_search_filter. Finally, the OpenAIClient
    is closed and the function returns the ai_search_filter and the category.
    """

    category = None
    ai_search_filter = None

    i = 0

    for message in system_messages:
        openai_category_response = await openai_client.chat_completion(
            system_message=message, message_text=message_text, openai_max_message_length=openai_max_message_length
        )
        if category and openai_category_response:
            category = f"{category}_{openai_category_response}"
        else:
            category = openai_category_response
        if i == 0:
            ai_search_filter = openai_category_response
            i += 1
    return ai_search_filter, category


# system prompt messages
issue_contains_enough_detailed_information_msg = (
    'Answer me with "yes" or "no" if the following request is detailed enough to give an answer:'
)
summarize_issue_msg = "Please summarize the user content"
mate_response_evaluation_msg = (
    "The user"
    "s his message includes an answer to a question. Assign one of the two labels to the user"
    's message based on its ability to solve the question: \n"Unable to Assist"\n"Able to Assist"\nThis was the initial question: '
)


async def main():
    logging.info("Starting the ticket bot")
    if SIMULATE:
        logging.info("Simulating the ticket bot")

    if jira_server is None or jira_username is None or jira_token is None or jira_jql is None:
        raise ValueError("JIRA_SERVER, JIRA_USERNAME, JIRA_TOKEN, and JIRA_JQL must be set")

    logging.info("Authenticating OpenAI client")
    openai_client: OpenAIClient = OpenAIClient(
        azure_openai_service=azure_openai_service,
        api_version=api_version,
        embedding_model=embedding_model,
        model=model,
    )
    # Authenticate and initialize the Jira client
    logging.info("Authenticating Jira client")
    jira_client = JiraClient(
        server=jira_server, username=jira_username, token=jira_token, openai_client=openai_client, simulate=SIMULATE
    )
    logging.info("Authenticating Mate client")
    mate_client = MateClient(
        jira_mate_tenant_id,
        jira_mate_sp_client_di,
        jira_mate_secret,
        jira_mate_scope,
        mate_backend_url,
    )
    # Get categories from Mate
    logging.info("Getting Mate categories")
    mate_categories = json.loads(mate_client.get_mate_categories())["categories"]
    # Get the issues from Jira
    logging.info(f"Getting issues from Jira with JQL {jira_jql}")
    issues = jira_client.get_issues(jira_jql)

    # Loop through the issues
    for issue in issues:
        if isinstance(issue, Issue):
            transition_to_an_agent = False
            categorization_input = None
            issue_contains_enough_detailed_information = None
            logging.info(f"Processing issue {issue.key}")

            if jira_categorization_field is not None:
                categorization_input = issue
                attrs = jira_categorization_field.split(".")
                for attr in attrs:
                    if categorization_input is not None:
                        categorization_input = getattr(categorization_input, attr, None)
                        logging.debug(f"Attribute {attr} of issue {issue.key} is {categorization_input}")
                    else:
                        break

            if jira_client.get_last_comment(issue.key) is not None:
                last_comment = str(jira_client.get_last_comment(issue.key))
                description = str(jira_client.read_ticket(issue.key)[1])
                categorization_input = last_comment + " " + description
                logging.debug(f"Categorization input for issue {issue.key} is {categorization_input}")

            else:
                description = str(jira_client.read_ticket(issue.key)[1])
                categorization_input = description
                logging.debug(f"Categorization input for issue {issue.key} is {categorization_input}")

            # Summarize the issue using OpenAI's ChatCompletion API
            logging.info(mate_label_system_messages)
            logging.info(type(mate_label_system_messages))
            logging.info(f"Summarizing issue {issue.key}")

            openai_summarized_issue = await openai_client.chat_completion(
                system_message=summarize_issue_msg,
                message_text=categorization_input,
                openai_max_message_length=openai_max_message_length,
            )

            logging.debug(f"Summarized issue for issue {issue.key} is {openai_summarized_issue}")

            if len(mate_label_system_messages) > 0 and len(mate_label_system_messages) < 11:
                (ai_search_category_filter, categories) = await categorize_content(
                    system_messages=mate_label_system_messages, openai_client=openai_client, message_text=openai_summarized_issue
                )
                logging.info(f"Mate categories are {categories}")
                mate_category_filter = next(
                    (key for key, values in mate_filter_label_mapping.items() if ai_search_category_filter in values),
                    None,
                )
                logging.info(f"Mate category filter is {mate_category_filter}")
            else:
                logging.error(f"The length of mate_label_system_messages is {len(mate_label_system_messages)}")
                logging.error(f"The type of mate_label_system_messages is {type(mate_label_system_messages)}")
                logging.error("Aborting")
                raise ValueError("The length of mate_label_system_messages must be between 1 and 10")

            if mate_category_filter is None or mate_category_filter not in mate_categories:
                overrides = None

            else:
                overrides = {"category_filter": [mate_category_filter]}
                logging.debug(f"Overrides for issue {issue.key} are {overrides}")
                logging.debug(f"Excluded Categories for issue {issue.key} are {excluded_categories}")

            if categories not in excluded_categories:
                logging.info(f"Try to get answer by Mate for {issue.key} with categories {categories}")
                mate_res = mate_client.get_answer(categorization_input, overrides)
                if not mate_res:
                    logging.info(f"Unable to get answer by Mate for {issue.key} with categories {categories}")
                    continue
                mate_response = json.loads(mate_res)
                # checking if Mate was able to assist
                logging.debug(f"Mate response for issue {issue.key} is {mate_response}")
                logging.info(f"Evaluating Mate response for issue {issue.key}")

                mate_response_evaluation = await openai_client.chat_completion(
                    system_message=mate_response_evaluation_msg + openai_summarized_issue,
                    message_text=mate_response["answer"],
                    openai_max_message_length=openai_max_message_length,
                )

                logging.debug(f"Mate response evaluation for issue {issue.key} is {mate_response_evaluation}")
                sources = ""
                logging.debug(f"data points for issue {issue.key} are {mate_response['data_points']}")

                for data_point in mate_response["data_points"]:
                    logging.info(f"Processing data points for issue {issue.key}")
                    if data_point["docName"].endswith(".pdf"):
                        sources = sources + data_point["docName"] + " Page: " + str(data_point["page"]) + "\n"
                    elif data_point["docName"].startswith("http"):
                        sources = sources + data_point["docName"] + "\n"

                if "Unable to Assist" in mate_response_evaluation:
                    logging.info(
                        f"Unable to assist for issue {issue.key} - checking if enough detailed information is given in the issue"
                    )
                    issue_contains_enough_detailed_information = await openai_client.chat_completion(
                        system_message=issue_contains_enough_detailed_information_msg,
                        message_text=openai_summarized_issue,
                        openai_max_message_length=openai_max_message_length,
                    )
                    if issue_contains_enough_detailed_information == "no":
                        logging.info(
                            f"Not enough detailed information for issue {issue.key} - asking customer for more information"
                        )
                        issue_response_text = (
                            issue_response_text
                        ) = f"""{'='*50}
    Issue:{issue.key}\n\n*Mate understood:*
    {openai_summarized_issue}\n*Mate category:*
    {mate_category_filter}\n*Mate search key words:*
    {mate_response['keywords']}\n\n*Mate response:*
    Please provide more detailed information for me to assist you.
    \n*{jira_message_text}{jira_transition_name_if_unable_to_assist}*\n
    {'='*50}"""
                    else:
                        logging.info(f"Enough detailed information for issue {issue.key} - transitioning to an agent")
                        transition_to_an_agent = True
                        issue_response_text = f"""{'='*50}
    Issue:{issue.key}\n\n*Mate understood:*
    {openai_summarized_issue}\n*Mate category:*
    {mate_category_filter}\n*Mate search key words:*
    {mate_response['keywords']}\n\n*Mate response:*
    Unable to assist automatically. Transitioning to an agent.
    \n*{jira_message_text}{jira_transition_name_if_unable_to_assist}*\n
    {'='*50}"""
                else:
                    logging.info(f"Able to assist for issue {issue.key} - transitioning to customer")
                    issue_response_text = f"""{'='*50}
    Issue:{issue.key}\n\n*Mate understood:*
    {openai_summarized_issue}\n*Mate category:*
    {mate_category_filter}\n*Mate search key words:*
    {mate_response['keywords']}\n\n*Mate response:*
    {mate_response['answer']}\n\n*Mate sources used/found:*
    {sources}
    \n*{jira_message_text}{jira_transition_name_if_unable_to_assist}*\n
    {'='*50}"""
                if SIMULATE:
                    logging.info(f"Simulating issue {issue.key} - not adding comment to the issue or transitioning issue")
                    print(issue_response_text)
                else:
                    try:
                        jira_client.add_comment(issue.key, issue_response_text)
                    except Exception as e:
                        logging.error(f"An error occurred while adding the comment: {e}")
                        continue
                    if mate_response_evaluation.replace('"', "") == "Able to Assist":
                        for data_point in mate_response["data_points"]:
                            logging.info(f"Processing data points for issue {issue.key}")
                            if data_point["docName"].endswith(".pdf"):
                                path = "/" + quote(data_point["docName"])
                                logging.info(f"Downloading PDF for issue {issue.key} from {path}")
                                pdf = mate_client.download_pdf(path)
                                # Create a temporary directory
                                logging.debug(f"Creating temporary file for issue {issue.key}")
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                                    if pdf:
                                        temp_file.write(pdf)
                                    else:
                                        logging.error(f"PDF for issue {issue.key} could not be downloaded")
                                        continue
                                logging.debug(f"Renaming temporary file for issue {issue.key}")
                                os.rename(
                                    temp_file.name,
                                    os.path.dirname(temp_file.name) + "/" + data_point["docName"],
                                )
                                attachment = os.path.dirname(temp_file.name) + "/" + data_point["docName"]
                                # Attach the file to the issue
                                logging.info(f"Attaching PDF {attachment} for issue {issue.key}")
                                jira_client.attach_file(issue.key, attachment)
                                logging.debug(f"Removing temporary file {attachment}")
                                os.unlink(attachment)
                    logging.info(f"Getting possible transitions for issue {issue.key}")
                    possible_transitions = jira_client.get_transitions(issue.key)
                    if not transition_to_an_agent:
                        logging.info(f"Getting transition id to answer the customer for issue {issue.key}")
                        transition_id = jira_client.get_transition_id(possible_transitions, jira_transition_name)
                    else:
                        logging.info(f"Getting transition id to transfer it to an agent for issue {issue.key}")
                        transition_id = jira_client.get_transition_id(
                            possible_transitions, jira_transition_name_if_unable_to_assist
                        )
                    try:
                        logging.info(f"Transitioning issue {issue.key} to transition id {transition_id}")
                        jira_client.transition_issue(issue.key, transition_id)
                    except Exception:
                        logging.warning(
                            f"Transitioning issue {issue.key} failed, because it may transitioned already automatically -- please check the issue in Jira."  # noqa
                        )
    logging.info("Ticket bot finished")

    if str.lower(os.getenv("AUTOMATIC_LEARNING", "false")) == "true":
        logging.info("Automatic Learning from answered tickets")

        answered_tickets = jira_client.identify_answered_tickets(
            str.lower(os.getenv("JIRA_ANSWERED_TICKET_KEYWORD", "goodanswerbyccoe"))
        )

        await jira_client.index_answered_tickets(
            answered_tickets,
            search_index=os.getenv("AZURE_SEARCH_INDEX", "gptkbindex"),
            search_service=os.getenv("AZURE_SEARCH_SERVICE", "service"),
        )
    else:
        logging.info("Automatic Learning is disabled")

    await openai_client.close()


if __name__ == "__main__":
    asyncio.run(main())
