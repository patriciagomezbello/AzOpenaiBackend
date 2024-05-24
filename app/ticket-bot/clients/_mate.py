import logging

import requests
from msal import ConfidentialClientApplication


class MateClient:
    """The MateClient class is a Python class designed to interact with a backend service, presumably named "Mate".

    The class is initialized with several parameters:

    tenant_id: The ID of the tenant in the Microsoft Azure service.
    jira_mate_client_id: The client ID for the Jira Mate service.
    jira_mate_client_secret: The client secret for the Jira Mate service.
    scope: The scope for the Microsoft Azure service.
    mate_backend_url: The URL of the Mate backend service.
    These parameters are stored in a configuration dictionary (self.config).

    The class also initializes a ConfidentialClientApplication from the Microsoft Authentication Library (MSAL).
    This application is used to authenticate with the Microsoft Azure service using the provided client ID,
    authority (constructed from the tenant ID), and client secret.

    The get_token method is used to acquire a token silently (without user interaction) from the Microsoft
    Azure service. If a token cannot be acquired silently, the method logs an info message
    (the logging message is not fully visible in the provided code).
    """

    def __init__(
        self,
        tenant_id,
        jira_mate_client_id,
        jira_mate_client_secret,
        scope,
        mate_backend_url,
    ):
        self.config = {
            "authority": "https://login.microsoftonline.com/" + tenant_id,
            "client_id": jira_mate_client_id,
            "client_secret": jira_mate_client_secret,
            "scope": [scope],
            "mate_backend_url": mate_backend_url,
        }
        self.app = ConfidentialClientApplication(
            self.config["client_id"],
            authority=self.config["authority"],
            client_credential=self.config["client_secret"],
        )

    def get_token(self):
        result = None
        result = self.app.acquire_token_silent(self.config["scope"], account=None)
        try:
            if not result:
                logging.info("No suitable token exists in cache. Let's get a new one from Azure AD.")
                result = self.app.acquire_token_for_client(scopes=self.config["scope"])

            if "access_token" in result:
                return result["access_token"]
            else:
                return None
        except Exception as e:
            print(e)
            raise

    def get_mate_categories(self):
        token = self.get_token()
        if token:
            headers = {"Authorization": "Bearer " + token}
            print(self.config["mate_backend_url"])
            response = requests.get(str(self.config["mate_backend_url"]) + "/categories", headers=headers)
            return response.text
        else:
            return None

    def get_answer(
        self,
        message_text,
        overrides=None,
        bot=None,
        max_message_text_length=3096,
        openai_max_tokens=2048,
    ):
        token = self.get_token()
        message = {
            "approach": "rrr",
            "history": [{"bot": bot, "user": message_text[:openai_max_tokens]}],
            "overrides": None,
        }
        if token:
            headers = {"Authorization": "Bearer " + token}
            response = requests.post(str(self.config["mate_backend_url"]) + "/chat", headers=headers, json=message)
            return response.text
        else:
            return None

    def download_pdf(self, path):
        token = self.get_token()
        if token:
            headers = {"Authorization": "Bearer " + token}
            response = requests.get(str(self.config["mate_backend_url"]) + "/content" + path, headers=headers)
            return response.content
        else:
            return None
