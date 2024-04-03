import requests
from jira import JIRA
import logging


class JiraClient:
    def __init__(self, server, username, token):
        self.server = server
        self.username = username
        self.token = token
        self.jira = self.authenticate_jira()

    def authenticate_jira(self):
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

    def read_ticket(self, ticket_id):
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
                issue.fields.description,
                issue.fields.status.name,
                issue.fields.assignee,
            )
        except Exception as e:
            logging.error(f"Ein Fehler ist aufgetreten: {e}")
            raise

    def get_issues(self, jql_str):
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
        status_name: The name of the status whose ID should
                      be returned.

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
        """
        Retrieves the transitions for a specific issue.

        Input parameters:
        issue_id: The ID of the issue for which the transitions should
                  be retrieved.

        Output parameters:
        Returns a list of transitions for the specified issue.
        """

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
        """
        Retrieves a specific transition from the provided JSON object.

        Input parameters:
        transitions: A list of transitions.
        transition_name: The name of the transition to be retrieved.

        Output parameters:
        Returns the ID of the specified transition if found, None otherwise.
        """
        for rec in transitions:
            if rec["name"] == transition_name:
                return rec["id"]
        logging.error(f"Transition {transition_name} wurde nicht gefunden.")
        return None

    def transition_issue(self, issue_id, transition_id):
        """
        Transitions an issue to a new state.

        Input parameters:
        issue_id: The ID of the issue to be transitioned.
        transition_id: The ID of the transition to be applied.

        Output parameters:
        None.
        """
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

    def get_last_comment(self, issue_id):
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
                response = requests.get(
                    attachment.content, auth=(self.username, self.token)
                )
                response.raise_for_status()
                return response.content
            else:
                logging.error(
                    "No attachment found with ID {attachment_id} for issue {issue_id}."
                )
                return None
        except Exception as e:
            logging.error(
                "An error occurred while downloading and reading the attachment:"
            )
            logging.error(e)
            raise
