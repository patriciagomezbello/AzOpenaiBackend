import logging
from abc import ABC
from abc import abstractmethod
from typing import cast
from typing import Optional
from typing import Sequence

import requests
from azure.identity.aio import DefaultAzureCredential
from dataloader.cli.core.parser import ParsedArgs
from dataloader.cli.core.service import Service
from dataloader.cli.core.utils import defer
from dataloader.cli.models.config import CLIConfig
from dataloader.dataloader.indexer import Indexer
from dataloader.dataloader.indexer.models.document import DocumentInfo
from dataloader.dataloader.loaders.blob import BlobInteractor
from jira import Issue
from jira import JIRA
from jira.client import ResultList
from jira.resources import Comment


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
    def __init__(self, server, username, token):
        self.server = server
        self.username = username
        self.token = token
        self.jira = self._authenticate()

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

    async def index_answered_tickets(self, answered_tickets: list[str], args: ParsedArgs) -> None:
        """
        Indexes the answered tickets.

        Input parameters:
        answered_tickets: A list of ticket IDs to be indexed.

        Output parameters:
        None.
        """
        try:
            credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
            config = CLIConfig.load(args)

            service = Service(
                BlobInteractor(account=config.storage_account, container=config.docs_container, credential=credential),
                Indexer(config=config.indexer_config, credential=credential),
                config,
            )

            async with defer(service.close, lambda e: logging.exception(f"An error occurred while running the data loader: {e}")):
                documents: Sequence[DocumentInfo] = []
                summary: dict[str, int] = {}

                docs, sum = await service.load_lc_mode()
                documents.extend(docs)
                summary.update(sum)

                await service.purge_chunk_corpses(summary=summary)

            documents = []
            for ticket_id in answered_tickets:
                summary, description, status, assignee, comments = self.read_ticket(ticket_id)
                document = {
                    "ticket_id": ticket_id,
                    "summary": summary,
                    "description": description,
                    "status": status,
                    "assignee": assignee,
                    "last_comment": comments[-1].body,
                }
                documents.append(DocumentInfo(**document))
                await service.indexer.index_documents(documents=documents)
        except Exception as e:
            logging.error(f"An error occurred while indexing the answered tickets: {e}")
            raise
