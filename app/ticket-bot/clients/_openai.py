import logging
from typing import Iterable

from azure.identity.aio import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessageParam


class OpenAIClient:
    """
    The OpenAIClient class is a Python class designed to interact with the OpenAI API.

    The class is initialized with several parameters:

    azure_openai_service: The Azure OpenAI service instance.
    api_version: The version of the OpenAI API to use.
    model: The model to use for the OpenAI API.
    These parameters are used to configure the OpenAI client.

    The class also contains methods to interact with the OpenAI API, such as chat_completion,
    which sends a message to the OpenAI API and receives a response. This method is asynchronous,
    meaning it returns a promise that resolves with the response from the OpenAI API.

    The close method is used to close the OpenAI client when it is no longer needed.
    This is important to free up resources and prevent memory leaks.
    """

    def __init__(
        self,
        azure_openai_service,
        model,
        api_version="2023-09-15-preview",
    ):
        """
        This is the constructor (__init__) of the OpenAIClient class. It initializes an instance of the class.

        Parameters:

        azure_openai_service: The Azure OpenAI service instance.
        model: The model to use for the OpenAI API. The default value is "gpt-4".
        api_version: The version of the OpenAI API to use. The default value is "2023-09-15-preview".

        """
        print(f"Initializing OpenAIClient with host: {azure_openai_service}")
        self.model = model
        self.azure_openai_service = azure_openai_service

        self.azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

        # OpenAI setup
        self.token_provider = get_bearer_token_provider(self.azure_credential, "https://cognitiveservices.azure.com/.default")
        self.openaiClient = AsyncAzureOpenAI(
            api_version=api_version,
            azure_endpoint=f"https://{azure_openai_service}.openai.azure.com",
            azure_ad_token_provider=self.token_provider,
        )

    async def chat_completion(self, system_message: str, message_text: str, openai_max_message_length=1000):
        """chat_completion method sends a message to the OpenAI API and receives a response."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message_text},
        ]
        try:
            response = await self.openaiClient.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=0.7,
                max_tokens=800,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
            )
            return response.choices[0].message.content

        except Exception as e:
            if "context_length_exceeded" in str(e):
                logging.warning(f"{e}")
                logging.warning(f"Reducing length of the message to {openai_max_message_length} characters and try it again")
                shortened_text = message_text[: int(openai_max_message_length)]
                messages: Iterable[ChatCompletionMessageParam] = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": shortened_text},
                ]

                response = await self.openaiClient.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800,
                    top_p=0.95,
                    frequency_penalty=0,
                    presence_penalty=0,
                    stop=None,
                )
                return response.choices[0].message.content
            else:
                logging.critical(f"ERROR: {e}")
                raise

    async def close(self):
        await self.openaiClient.close()
        await self.azure_credential.close()
