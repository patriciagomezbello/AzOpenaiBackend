import base64
import logging
import os
from abc import ABC
from abc import abstractmethod
from typing import cast
from typing import Generator
from typing import List
from typing import Optional

import pycountry
import requests
from _openai import OpenAIClient
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from jira import Issue
from jira import JIRA
from jira.client import ResultList
from jira.resources import Comment
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lingua import Language
from lingua import LanguageDetector
from lingua import LanguageDetectorBuilder


class Jira(ABC):
    @abstractmethod
    def read_ticket(self, ticket_id, with_last_comment): ...

    @abstractmethod
    def get_issues(self, jql_str): ...

    @abstractmethod
    def get_default_status_ids(self, status_name): ...

    @abstractmethod
    def get_transitions(self, issue_id): ...

    @abstractmethod
    def get_transition_id(self, transitions, transition_name): ...

    @abstractmethod
    def transition_issue(self, issue_id, transition_id): ...

    @abstractmethod
    def add_comment(self, issue_id, comment): ...

    @abstractmethod
    def get_last_comment(self, issue_id): ...

    @abstractmethod
    def attach_file(self, issue_id, file_path): ...

    @abstractmethod
    def read_attachment(self, issue_id, attachment_id): ...


class JiraClient(Jira):
    def __init__(self, server: str, username: str, token: str, openai_client: OpenAIClient, simulate: bool):
        self.server = server
        self.username = username
        self.token = token
        self.jira = self._authenticate()
        self.openai_client = openai_client
        self.simulate = simulate

    def _authenticate(self):
        """
        Authenticates with the Jira server.

        Input parameters:
        server: The Jira server URL.
        username: The username for Jira authentication.
        token: The token for Jira authentication.

        Output parameters:
        Returns a Jira object if authentication is successful, None otherwise.
        """
        try:
            jira = JIRA(server=self.server, basic_auth=(self.username, self.token))
            return jira
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

    def read_ticket(self, ticket_id) -> tuple[str, str, str, str, list[Comment]]:
        """
        Reads the details of a specific Jira ticket.

        Input parameters:
        jira_auth_obj: A Jira authentication object.
        ticket_id: The ID of the ticket to be read.

        Output parameters:
        Returns the summary, description, status name, assignee of the ticket.
        """
        try:
            issue = self.jira.issue(ticket_id)
            return (
                issue.fields.summary,
                issue.fields.description or "",
                cast(str, issue.fields.status.name),
                cast(str, issue.fields.assignee),
                issue.fields.comment.comments,
            )
        except Exception as e:
            logging.error(f"Ein Fehler ist aufgetreten: {e}")
            raise

    def get_issues(self, jql_str: str):
        """
        Executes a JQL query and returns the resulting issues.

        Input parameters:
        jira_auth_obj: A Jira authentication object.
        jql_str: The JQL string to be executed.

        Output parameters:
        Returns a list of the resulting issues.
        """
        try:
            return self.jira.search_issues(jql_str)
        except Exception as e:
            logging.error(f"Ein Fehler ist aufgetreten: {e}")
            raise

    def get_default_status_ids(self, status_name):
        """
        Searches for a specific default status and returns its ID.

        Input parameters:
        jira: A Jira object.
        status_name: The name of the status whose ID should be returned.

        Output parameters:
        Returns the name and ID of the status.
        """
        # Get all statuses
        statuses = self.jira.statuses()

        for status in statuses:
            if status.name == status_name:
                return status.name, status.id

        # Status not found
        logging.warning(f"Status {status_name} wurde nicht gefunden.")
        return None

    def get_transitions(self, issue_id):
        """get_transitions retrieves the transitions for a specific issue."""

        url = f"{self.server}/rest/api/2/issue/{issue_id}/transitions"
        try:
            r = requests.get(url, auth=(self.username, self.token))
            r.raise_for_status()
            transitions = r.json()["transitions"]
            return transitions
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP-Fehler aufgetreten: {http_err}")
            raise
        except Exception as err:
            logging.error(f"Ein Fehler ist aufgetreten: {err}")
            raise

    def get_transition_id(self, transitions, transition_name):
        """get_transition_id retrieves a specific transition from the provided JSON object."""
        for rec in transitions:
            if rec["name"] == transition_name:
                return rec["id"]
        logging.error(f"Transition {transition_name} wurde nicht gefunden.")
        return None

    def transition_issue(self, issue_id, transition_id):
        """transition_issue transitions an issue to a new state."""
        try:
            issue = self.jira.issue(issue_id)
            self.jira.transition_issue(issue, transition_id)
        except Exception as e:
            logging.error(f"An error occurred while transitioning the issue: {e}")
            raise

    def add_comment(self, issue_id, comment):
        """
        Adds a comment to an issue.

        Input parameters:
        issue_id: The ID of the issue to which the comment should be added.
        comment: The text of the comment to be added.

        Output parameters:
        None.
        """
        try:
            issue = self.jira.issue(issue_id)
            self.jira.add_comment(issue, comment)
        except Exception as e:
            logging.error(f"An error occurred while adding the comment: {e}")
            raise

    def get_last_comment(self, issue_id: str) -> Optional[str]:
        """
        Retrieves the last comment from an issue.

        Input parameters:
        issue_id: The ID of the issue from which the comment should be
                retrieved.

        Output parameters:
        Returns the text of the last comment if found, None otherwise.
        """
        try:
            issue = self.jira.issue(issue_id)
            comments = issue.fields.comment.comments
            if comments:
                return comments[-1].body
            else:
                logging.error(f"No comments found for issue {issue_id}.")
                return None
        except Exception as e:
            logging.error(f"An error occurred while retrieving the comment: {e}")
            raise

    def attach_file(self, issue_id, file_path):
        """
        Attaches a file to an issue.

        Input parameters:
        issue_id: The ID of the issue to which the file should be attached.
        file_path: The path of the file to be attached.

        Output parameters:
        None.
        """
        try:
            issue = self.jira.issue(issue_id)
            self.jira.add_attachment(issue=issue, attachment=file_path)
        except Exception as e:
            logging.error(f"An error occurred while attaching the file: {e}")
            raise

    def read_attachment(self, issue_id, attachment_id):
        """
        Downloads and reads an attachment from an issue.

        Input parameters:
        issue_id: The ID of the issue from which the attachment should be
                  downloaded.
        attachment_id: The ID of the attachment to be downloaded.

        Output parameters:
        Returns the content of the attachment if found, None otherwise.
        """
        try:
            issue = self.jira.issue(issue_id)
            attachment = [a for a in issue.fields.attachment if a.id == attachment_id]
            if attachment:
                attachment = attachment[0]
                response = requests.get(attachment.content, auth=(self.username, self.token))
                response.raise_for_status()
                return response.content
            else:
                logging.error("No attachment found with ID {attachment_id} for issue {issue_id}.")
                return None
        except Exception as e:
            logging.error("An error occurred while downloading and reading the attachment:")
            logging.error(e)
            raise

    def identify_answered_tickets(self, keyword: str) -> list[str]:
        """
        Identifies if a ticket has been answered by checking the last comment.

        Input parameters:
        ticket_id: The ID of the ticket to be checked.

        Output parameters:
        Returns True if the ticket has been answered, False otherwise.
        """
        try:
            answered_tickets = []
            jql_query = "updated >= startOfDay(-1) AND updated <= endOfDay()"
            issues = self.get_issues(jql_str=jql_query)
            issues = cast(ResultList[Issue], issues)

            for issue in issues:
                last_comment = self.get_last_comment(issue.id)
                if last_comment is None:
                    continue
                if keyword not in last_comment:
                    continue
                logging.info(f"Identified answered ticket: {issue.key}")
                answered_tickets.append(issue.id)

        except Exception as e:
            logging.error(f"An error occurred while identifying the answered ticket: {e}")
        finally:
            return answered_tickets

    def _url_to_id(self, url: str, counter_dict: dict[str, int]):
        # check if url is already in counter_dict, if not, add it and initialize with 0
        if counter_dict.get(url) is not None:
            counter_dict[url] += 1
        else:
            counter_dict[url] = 0

        # add counter value and increase counter in counter_dict for the source

        url_hash = base64.b16encode(url.encode("utf-8")).decode("ascii")
        return f"url-{url_hash}-{str(counter_dict[url])}"

    def _split_text(
        self, document_map: List[tuple[str, str, str]], section_overlap=100, max_section_length=1500
    ) -> Generator[tuple[str, str, str]]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_section_length,
            chunk_overlap=section_overlap,
        )

        for val in document_map:
            s_text = splitter.split_text(val[2])
            for text in s_text:
                yield (val[0], val[1], text)

    def _detect_lang(self, text: str, detector, defaultLang="de"):
        try:
            lang = str(detector.detect_language_of(text))
            language = lang.split(".")[1].capitalize()
            iso_lang = pycountry.languages.get(name=language).alpha_2
            return iso_lang
        except Exception as e:
            print(e)
            return defaultLang

    async def index_answered_tickets(self, answered_tickets: list[str], search_service: str, search_index: str) -> None:
        """
        Indexes the answered tickets.

        Input parameters:
        answered_tickets: A list of ticket IDs to be indexed.

        Output parameters:
        None.
        """
        try:
            if len(answered_tickets) == 0:
                logging.info("No answered tickets found.")
                return

            credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
            search_client = SearchClient(
                endpoint=f"https://{search_service}.search.windows.net/",
                index_name=search_index,
                credential=credential,
            )

            documents: list[tuple[str, str, str]] = []
            for ticket_id in answered_tickets:
                summary, description, _, _, comments = self.read_ticket(ticket_id)

                link = f"{self.server}/browse/{ticket_id}"  # TODO: check correct link

                document: tuple[str, str, str] = (
                    link,
                    f"{self.server}/browse",
                    f" Issue: {description} \n\n, Summary: {summary} \n\n Solution and comments: {comments}",
                )

                documents.append(document)

            for doc in documents:
                exists = await search_client.get_document(key=self._url_to_id(doc[0], {}))
                if not exists:
                    logging.info("Document already exists in the index, will be removed for indexing")
                    documents.remove(doc)

            # build languages for usage
            detector: LanguageDetector = LanguageDetectorBuilder.from_languages(
                Language.ENGLISH,
                Language.GERMAN,
            ).build()

            counter_dict: dict[str, int] = {}

            for _, (source, base, section) in enumerate(
                self._split_text(
                    document_map=documents,
                )
            ):

                id = self._url_to_id(source, counter_dict)

                # Attempt to create an OpenAI Embedding for the input text section
                if self.simulate:
                    logging.info(f"Simulating indexing section {id} from source {source} with content: \n\n {section}")
                    break

                emb = await self.openai_client.create_embedding(text=section)

                if emb is not None:
                    # Return a dictionary with the processed section details, like id, content, embedding, etc.
                    # if category is None or role_config is None:
                    #     roles = ["public"]
                    # else:
                    #     roles = role_config.get(category, ["public"])
                    roles = ["public"]
                    category = os.getenv("JIRA_CATEGORY", None)  # TODO: check to get ticket category

                    section = {
                        "id": id,
                        "content": section,
                        "embedding": emb,
                        "doclang": self._detect_lang(text=section, detector=detector),
                        "category": category,
                        "roles": roles,
                        "sourcepage": source,
                        "sourcefile": base,
                    }
                else:
                    raise ValueError("No embedding was created")

                await search_client.upload_documents(documents=[section])

        except Exception as e:
            logging.error(f"An error occurred while indexing the answered tickets: {e}")
            raise
