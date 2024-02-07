from typing import Any
import time
import json
import os
from openai import AsyncOpenAI
from openai import RateLimitError
from openai.types.chat import ChatCompletion
from openai.types.create_embedding_response import CreateEmbeddingResponse
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType
from approaches.approach import ChatApproach
from core.messagebuilder import MessageBuilder
from core.modelhelper import (
    get_token_limit,
    addTokenCount,
    getCitationObject,
    detectLang,
    getLang,
    translateText,
    replace_abbreviations,
    applicationLog,
)
from text import nonewlines

from core.context import system_message_chat_conversation, query_prompt_template
from core.abbrev import abbreviations

DEBUG = False
DEBUG_MODE = os.getenv("DEBUG_MODE", "False")

if DEBUG_MODE == "TRUE":
    DEBUG = True


class ChatReadRetrieveReadApproach(ChatApproach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    system_message_chat_conversation = system_message_chat_conversation
    query_prompt_template = query_prompt_template

    # init function for the extended approach class for crrr
    def __init__(
        self,
        search_client: SearchClient,
        openai_client: AsyncOpenAI,
        chatgpt_deployment: str,
        chatgpt_model: str,
        embedding_deployment: str,
        sourcepage_field: str,
        content_field: str,
        max_tokens_query: int,
        max_tokens_answer: int,
    ):
        self.search_client = search_client
        self.openai_client = openai_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)
        self.max_tokens_query = max_tokens_query
        self.max_tokens_answer = max_tokens_answer

    # executable function that is connected to the chat api
    # -> receives and responds like chatgpt but with enterprise data
    async def run(
        self, history: list[dict[str, str]], overrides: dict[str, Any]
    ) -> Any:

        use_semantic_captions = True if overrides.get("semantic_captions") else False

        top = overrides.get("top") or 3

        filter_category = overrides.get("category_filter") or None

        category_filter = (
            " or ".join(
                "category eq '{}'".format(x.replace("'", "''")) for x in filter_category
            )
            if filter_category
            else None
        )

        if DEBUG:
            applicationLog(message="Debug Mode is on", level="info")

            if category_filter:
                debug_category = "DEBUG -> Category filter: " + category_filter
                applicationLog(message=debug_category, level="info")

        # Define the most common language stored in the search index as default.
        lang_facets = json.loads(os.getenv("FACETS_RESULTS").replace("'", '"'))
        default_lang = (
            getLang(lang_facets[0]["value"])
            if lang_facets
            else {"iso": "de", "name": "German"}
        )

        supported_languages = []
        for rec in lang_facets:
            supported_languages.append(getLang(rec["value"]))

        # Multilngual search is the default.
        # It is prior because it handles english text and german language in screen shots better - or vice versa ;-)
        multilingual_search = overrides.get("multilingual_search") or True

        # Do not allow too short questions without notice
        if len(history[-1]["user"]) > 9:
            user_prompt_lang = detectLang(history[-1]["user"])
            user_prompt_lang_name = getLang(user_prompt_lang)["name"]
        else:
            user_prompt_lang = default_lang["iso"]
            user_prompt_lang_name = default_lang["name"]

        noidea_de_text = "Tut mir leid, ich kann Ihnen nicht weiterhelfen. Bitte geben Sie eine spezifischere Frage ein"

        # Search without filters
        if multilingual_search:
            lang = default_lang["iso"]
            lang_name = default_lang["name"]
            lang_filter = ""
        # Search with language filters
        else:
            lang_name = next(
                (
                    rec.get("name")
                    for rec in supported_languages
                    if user_prompt_lang in rec["iso"]
                ),
                default_lang["name"],
            )
            lang = next(
                (
                    rec.get("iso")
                    for rec in supported_languages
                    if user_prompt_lang in rec["iso"]
                ),
                default_lang["iso"],
            )
            lang_filter = "doclang eq '{}'".format(lang)

        system_message_noidea = (
            noidea_de_text
            if user_prompt_lang == "de"
            else (
                await translateText(
                    self.openai_client,
                    noidea_de_text,
                    user_prompt_lang_name,
                    self.chatgpt_deployment,
                )
                if user_prompt_lang != "de"
                else "Sorry, I don't know"
            )
        )

        # build final filter
        print(f"lang filter: {lang_filter}")
        if lang_filter:
            print("lang_filter is existing")
            filter = lang_filter + (
                " and " + category_filter if category_filter else ""
            )
        else:
            filter = category_filter if category_filter else ""

        ques = history[-1]["user"]

        if DEBUG:
            debug_filter = "DEBUG -> Final filter: " + filter
            applicationLog(message=debug_filter, level="info")

        # handle abbreviations
        if len(abbreviations) > 0:
            try:
                temp = replace_abbreviations(ques, abbreviations)
                ques = temp
            except Exception:
                ques = history[-1]["user"]

        user_q = "Generate search query for: " + ques

        if DEBUG:
            debug_user_q = "DEBUG -> User query: " + user_q
            applicationLog(message=debug_user_q, level="info")

        # start logging full request time
        start_chat = time.perf_counter()

        # variables for potential exception
        error_res = None
        errorMessage = None

        # variable for response

        chat_content = None

        # time logging decimals
        r_dec = 4

        # initialize logging times as zero for error handling
        (
            chat_time,
            keyword_request_time,
            embedding_request_time,
            cog_search_request_time,
            main_llm_req_time,
        ) = (0, 0, 0, 0, 0)

        # initialize usedTokens for logging
        usedTokens: dict = {}

        try:
            # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
            messages = self.get_messages_from_history(
                self.query_prompt_template.format(language=lang_name),
                self.chatgpt_model,
                history,
                user_q,
                self.chatgpt_token_limit - len(user_q),
            )

            # start timing request
            start_keyword = time.perf_counter()

            # completion request to openAI to receive the keyword search query
            chat_completion: ChatCompletion = (
                await self.openai_client.chat.completions.create(
                    model=(
                        self.chatgpt_deployment
                        if self.chatgpt_deployment
                        else self.chatgpt_model
                    ),
                    messages=messages,
                    temperature=0.0,
                    max_tokens=self.max_tokens_query,
                    n=1,
                )
            )

            query_text = chat_completion.choices[0].message.content

            if query_text is None:
                raise ValueError("No query generated")

            if query_text.strip() == "0":
                query_text = history[-1][
                    "user"
                ]  # Use the last user input if we failed to generate a better query

            if DEBUG:
                debug_query = "DEBUG -> Generated query: " + query_text
                applicationLog(message=debug_query, level="info")

            addTokenCount(usedTokens, chat_completion)

            # save time for completion request for keyword optimization and add token count to request token object
            keyword_request_time = round(time.perf_counter() - start_keyword, r_dec)

            # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
            # retrieval mode is always hybrid
            start_embedding = time.perf_counter()

            # create embedding with text-ada002 model
            query_vector_embedding: CreateEmbeddingResponse = (
                await self.openai_client.embeddings.create(
                    model=self.embedding_deployment, input=query_text
                )
            )
            query_vector = query_vector_embedding.data[0].embedding

            addTokenCount(usedTokens, query_vector_embedding)

            embedding_request_time = round(time.perf_counter() - start_embedding, r_dec)

            # cog search lexicon speller query language dict of supported languages
            # cgs_query_languages = {
            #     "en": "en-us",
            #     "de": "de-de",
            #     "es": "es-es",
            #     "fr": "fr-fr",
            #     "nl": "nl-nl",
            # }

            start_cog_search = time.perf_counter()

            # Perform cognitive search

            # semantic ranker -> turned on (default)
            r = await self.search_client.search(
                query_text,
                filter=filter,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                top=top,
                query_caption=(
                    "extractive|highlight-false" if use_semantic_captions else None
                ),
                vector_queries=[
                    {
                        "kind": "vector",
                        "fields": "embedding",
                        "vector": query_vector,
                    }
                ],  # type: ignore
            )

            cog_search_request_time = round(
                time.perf_counter() - start_cog_search, r_dec
            )

            if use_semantic_captions:
                results = [
                    doc[self.sourcepage_field]
                    + ": "
                    + nonewlines(" . ".join([c.text for c in doc["@search.captions"]]))
                    async for doc in r
                ]
            else:
                # semantic captions turned off (default)
                results = [
                    doc[self.sourcepage_field]
                    + ": "
                    + nonewlines(doc[self.content_field])
                    async for doc in r
                ]
            content = "\n".join(results)

            if DEBUG:
                debug_results = "DEBUG -> Retrieved results from search: " + content
                applicationLog(message=debug_results, level="info")

            # STEP 3: Generate a contextual and content specific answer using the search results and chat history

            # define system message for final RAG approach
            system_message = self.system_message_chat_conversation.format(
                noidea=system_message_noidea,
                promptlang=user_prompt_lang_name,
                injected_prompt="",
            )

            if DEBUG:
                debug_system_message = "DEBUG -> System message: " + system_message
                applicationLog(message=debug_system_message, level="info")

            main_llm_req_start = time.perf_counter()

            # Execute Request against GPT3.5 or 4 that includes company/custom data
            messages = self.get_messages_from_history(
                system_message,
                self.chatgpt_model,
                history,
                history[-1]["user"] + "\n\nSources:\n" + content,
                max_tokens=self.chatgpt_token_limit,
            )
            # Model does not handle lengthy system messages well.
            # Moving sources to latest user conversation to solve follow up questions prompt.

            chat_completion = await self.openai_client.chat.completions.create(
                model=(
                    self.chatgpt_deployment
                    if self.chatgpt_deployment
                    else self.chatgpt_model
                ),
                messages=messages,
                temperature=overrides.get("temperature") or 0.7,
                max_tokens=self.max_tokens_answer,
                n=1,
            )

            chat_content = chat_completion.choices[0].message.content

            if chat_content is None:
                raise ValueError("No chat content generated")

            if DEBUG:
                debug_chat_content = "DEBUG -> Generated chat content: " + chat_content
                applicationLog(message=debug_chat_content, level="info")

            addTokenCount(usedTokens, chat_completion)

            main_llm_req_time = round(time.perf_counter() - main_llm_req_start, r_dec)

            chat_time = round(time.perf_counter() - start_chat, r_dec)

        # handle all errors except rate limit the same, as no difference is needed here
        except Exception as e:
            if isinstance(e, RateLimitError):
                errorMessage = str(e)
                error_res = {"error": "rate limit exceeded", "code": 429}
            else:
                errorMessage = str(e.args[0])
                error_res = {"error": errorMessage, "code": 500}

            log_values = {
                "status": "error",
                "error_message": errorMessage,
                "full_chat_time": chat_time,
                "keyword_opt_time": keyword_request_time,
                "embedding_time": embedding_request_time,
                "search_time": cog_search_request_time,
                "main_req_time": main_llm_req_time,
            }
            applicationLog(json.dumps(log_values), "error")

            if DEBUG:
                debug_error = "DEBUG -> Error message: " + errorMessage
                applicationLog(message=debug_error, level="error")

            return error_res

        # define logs for applicationinsights
        log_values = {
            "status": "ok",
            "full_chat_time": chat_time,
            "keyword_opt_time": keyword_request_time,
            "embedding_time": embedding_request_time,
            "search_time": cog_search_request_time,
            "main_req_time": main_llm_req_time,
        }

        # add dynamically all used tokens
        for key, value in usedTokens.items():
            log_values[key] = value

        citationList = getCitationObject(chat_content) if chat_content else []

        return {
            "data_points": citationList,
            "answer": chat_content,
            "keywords": query_text,
        }

    # function to extract the messages from the history and transform them into the correct format
    def get_messages_from_history(
        self,
        system_prompt: str,
        model_id: str,
        history: list[dict[str, str]],
        user_conv: str,
        few_shots=[],
        max_tokens: int = 4096,
    ) -> list:
        message_builder = MessageBuilder(system_prompt, model_id)

        user_content = user_conv

        message_builder.append_message(self.USER, user_content)

        for h in reversed(history[:-1]):
            if bot_msg := h.get("bot"):
                message_builder.append_message(self.ASSISTANT, bot_msg)
            if user_msg := h.get("user"):
                message_builder.append_message(self.USER, user_msg)
            if message_builder.token_length > max_tokens:
                break

        messages = message_builder.messages
        return messages
