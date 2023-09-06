from typing import Any
import time
import json 
import os

import openai
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType

from approaches.approach import ChatApproach
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit, num_tokens_from_messages,addTokenCount, getCitationObject, detectLang, getLang, translateText, replace_abbreviations
from text import nonewlines

from core.context import system_message_chat_conversation, query_prompt_template
from core.abbrev import abbreviations


class ChatReadRetrieveReadApproach(ChatApproach):
    # Chat roles
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    
    system_message_chat_conversation = system_message_chat_conversation
    query_prompt_template = query_prompt_template

    # init function for the extended approach class for crrr
    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, chatgpt_model: str, embedding_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.chatgpt_model = chatgpt_model
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.chatgpt_token_limit = get_token_limit(chatgpt_model)

    # executable function that is connected to the chat api -> receives and responds like chatgpt but with enterprise data‚
    async def run(self, history: list[dict[str, str]], overrides: dict[str, Any]) -> Any:
        
        #initialize overrides
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        ''' Building the category filter in dependence of the given path >ToDo: must be implemented'''
        exclude_category = overrides.get("exclude_category") or None
        category_filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
        ''' Building the language filter accordig to the language in the user prompt and in dependence of multilingual_search setting (True|False)'''
        lang_facets = json.loads(os.getenv('FACETS_RESULTS').replace("'", '"'))
        print(lang_facets)
        default_lang = getLang(lang_facets[0]['value']) if lang_facets else {'iso': 'de','name': 'German'}
        print('The default lang is: ' + str(default_lang)) 
        supported_languages = []
        for rec in lang_facets:
            supported_languages.append(getLang(rec['value']))
        print('Supported Languages : ' + str(supported_languages))
        user_prompt_lang = detectLang(history[-1]["user"])
        user_prompt_lang_name = getLang(user_prompt_lang)
        lang_name = next((rec.get('name') for rec in supported_languages if user_prompt_lang in rec['iso']), default_lang['name'])
        lang = next((rec.get('iso') for rec in supported_languages if user_prompt_lang in rec['iso']), default_lang['iso'])
        noidea_de_text = 'Tut mir leid, ich weiss das nicht'
        system_message_noidea = noidea_de_text if lang == 'de' else translateText(noidea_de_text, user_prompt_lang_name['name'],self.chatgpt_deployment) if lang != 'de' else "Sorry, I don't know"
        ''' Multilngual search is the default. It is prior because it handles english text and german language in screen shots better '''
        multilingual_search = overrides.get("multilingual_search") or True
        lang_filter = "doclang eq '{}'".format(lang) if (multilingual_search is None or multilingual_search is False) else ''

        
        filter = lang_filter + (' and ' + category_filter if category_filter else '')
        print("Using Filter :" + filter)
        ques = history[-1]["user"]


        if(len(abbreviations) > 0):
                    try: 
                        temp = replace_abbreviations(ques, abbreviations)
                        ques = temp
                    except:
                        ques = history[-1]["user"]
                    
        
        user_q = 'Generate search query for: ' + ques
        

        # start logging full request time
        start_chat = time.perf_counter()
        
        # variable for exception
        exc = False

        # time logging decimals
        r_dec = 4

        # initialize logging times as zero for error handling
        chat_time, keyword_request_time, embedding_request_time, cog_search_request_time, main_llm_req_time = 0,0,0,0,0

        # initialize usedTokens for logging
        usedTokens: dict = {}
        try:

            # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
            messages = self.get_messages_from_history(
                self.query_prompt_template.format(language=lang_name),
                self.chatgpt_model,
                history,
                user_q,
                self.chatgpt_token_limit - len(user_q)
            )
            
            # start timing request
            start_keyword = time.perf_counter()

            try: 
                # completion request to openAI

                chat_completion = await openai.ChatCompletion.acreate(
                    deployment_id=self.chatgpt_deployment,
                    model=self.chatgpt_model,
                    messages=messages, 
                    temperature=0.0, 
                    max_tokens=32, 
                    n=1)
                
                query_text = chat_completion.choices[0].message.content

                if query_text.strip() == "0":
                    query_text = history[-1]["user"] # Use the last user input if we failed to generate a better query

                addTokenCount(usedTokens, chat_completion)

                # debug
                print(f"\nUmwandlung der Frage in Keywords: {query_text}\n")

            except Exception as e:
                raise Exception({
                    'exception': e.args[0], 
                    'info': {
                        'tokens': num_tokens_from_messages(messages, self.chatgpt_model)
                    }
                    })

            # save time for completion request for keyword optimization and add token count to request token object
            keyword_request_time = round(time.perf_counter() - start_keyword, r_dec)

            # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

            # If retrieval mode includes vectors, compute an embedding for the query
            if has_vector:
                
                start_embedding = time.perf_counter()

                try:
                    query_vector_embedding = await openai.Embedding.acreate(
                        engine=self.embedding_deployment, 
                        input=query_text)
                    query_vector = query_vector_embedding.data[0].embedding

                    addTokenCount(usedTokens, query_vector_embedding)

                except Exception as e: 
                    raise Exception({
                        'exception': e.args[0], 
                        'info': {
                            'tokens': num_tokens_from_messages(query_text, 'text-embedding-ada-002')
                            }})

                embedding_request_time = round(time.perf_counter() - start_embedding, r_dec)

            else:
                query_vector = None

            # Only keep the text query if the retrieval mode uses text, otherwise drop it
            if not has_text:
                query_text = None
            
            # cog search lexicon speller query language dict of supported languages
            cgs_query_languages = {'en': 'en-us', 'de': 'de-de', 'es': 'es-es', 'fr': 'fr-fr','nl': 'nl-nl'}
            
            start_cog_search = time.perf_counter()

            if overrides.get("semantic_ranker") and has_text:
                try:
                    r = await self.search_client.search(
                        query_text, 
                        filter=filter,
                        query_type=QueryType.SEMANTIC, 
                        query_language= cgs_query_languages.get(lang,'en-us'), 
                        query_speller="lexicon", 
                        semantic_configuration_name="default", 
                        top=top, 
                        query_caption="extractive|highlight-false" if use_semantic_captions else None,
                        vector=query_vector,
                        top_k=50 if query_vector else None,
                        vector_fields="embedding" if query_vector else None)
                    
                except Exception as e: 
                    raise Exception({
                        'exception': e.args[0],
                        'info': {
                            'top': top, 
                            'query_text': query_text
                            }})
                
            else:
                try:
                    r = await self.search_client.search(
                        query_text, 
                        filter=filter, 
                        query_language= cgs_query_languages.get(lang,'en-us'), 
                        top=top, 
                        vector=query_vector,
                        top_k=50 if query_vector else None, 
                        vector_fields="embedding" if query_vector else None)
                except Exception as e: 
                    raise Exception({
                        'exception': e.args[0],
                        'info': {
                            'top': top, 
                            'query_text': query_text
                            }})
                
            
            cog_search_request_time = round(time.perf_counter() - start_cog_search, r_dec)
            
            if use_semantic_captions:
                results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) async for doc in r]
            else:
                results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) async for doc in r]
            content = "\n".join(results)

            # debug
            print(f"\nContent aus der Suche: \n-----\n{content}\n-----\n")


            # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
            prompt_override = overrides.get("prompt_override")
            if prompt_override is None:
                system_message = self.system_message_chat_conversation.format(noidea=system_message_noidea, injected_prompt="")
            elif prompt_override.startswith(">>>"):
                system_message = self.system_message_chat_conversation.format(injected_prompt=prompt_override[3:] + "\n")

            # STEP 3: Generate a contextual and content specific answer using the search results and chat history
            main_llm_req_start = time.perf_counter()

            try:

                messages = self.get_messages_from_history(
                            system_message,
                            self.chatgpt_model,
                            history,
                            history[-1]["user"]+ "\n\nSources:\n" + content, # Model does not handle lengthy system messages well. Moving sources to latest user conversation to solve follow up questions prompt.
                            max_tokens=self.chatgpt_token_limit)

                chat_completion = await openai.ChatCompletion.acreate(
                    deployment_id=self.chatgpt_deployment,
                    model=self.chatgpt_model,
                    messages=messages, 
                    temperature=overrides.get("temperature") or 0.7, 
                    max_tokens=2048, 
                    n=1)
                
                addTokenCount(usedTokens, chat_completion)


            except Exception as e: 
                    raise Exception({
                        'exception': e.args[0],
                        'info': {
                            'prompt': num_tokens_from_messages(messages, self.chatgpt_model), 
                            'query_text': query_text
                            }})
            
            main_llm_req_time = round(time.perf_counter() - main_llm_req_start, r_dec)

            chat_time = round(time.perf_counter() - start_chat, r_dec)

        # if one of the request fails, this new object will be appended to the logs    
        except Exception as e:
            exc = True
            errorMessage = e.args[0]

        # define logs for applicationinsights
        log_values = {
            "status": "ok",
            "search_type": overrides.get("retrieval_mode"),
            "full_chat_time": chat_time, 
            "keyword_opt_time": keyword_request_time,
            "embedding_time": embedding_request_time,
            "search_time": cog_search_request_time,
            "main_req_time": main_llm_req_time
            }
        
        # add dynamically all used tokens
        for key, value in usedTokens.items():
            log_values[key] = value

        if exc: 
            log_values["status"] = "error"
            log_values["errorMessage"] = errorMessage

        # add to properties for usage in logger
        properties = {"custom_dimensions": log_values}

        #TODO: implement .env (not pushed to gitlab) logic for the logs 
        # logger = logging.getLogger(__name__)
        # logger.addHandler(AzureLogHandler('put in connectionstring here')
        # logger.warning('chat_request', extra=properties)

        print(log_values)
        
        # get list of citatiuons in text and provide it as text seperated by a new line
        
        if exc:
            return -1
        
        # Extract sources with specific information to be used by potential frontend for single pages and full document usage

        chat_content = chat_completion.choices[0].message.content

        # debug
        print(f"\nAntwort von ChatGPT: \n-----\n{chat_content}\n-----\n")

        msg_to_display = '\n\n'.join([str(message) for message in messages])

        citationList = getCitationObject(chat_content)

        return {"data_points": citationList, "answer": chat_content, "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>')}
    
    def get_messages_from_history(self, system_prompt: str, model_id: str, history: list[dict[str, str]], user_conv: str, few_shots = [], max_tokens: int = 4096) -> list:
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
