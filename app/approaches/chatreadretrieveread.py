import openai
import time
from typing import Any, Sequence
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, Vector
from approaches.approach import Approach
from text import nonewlines
from core.helperFunctions import addTokenCount, getCitationObject, replaceCitations
from core.messagebuilder import MessageBuilder
from core.modelhelper import get_token_limit, num_tokens_from_messages
#from opencensus.ext.azure.log_exporter import AzureLogHandler
from context import system_message_chat_conversation, query_prompt_template

# Chat-read-retrieve-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.

class ChatReadRetrieveReadApproach(Approach):
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
    def run(self, history: Sequence[dict[str, str]], overrides: dict[str, Any]) -> Any:
        
        #initialize overrides
        has_text = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        has_vector = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_captions = True if overrides.get("semantic_captions") and has_text else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        user_q = 'Generate search query for: ' + history[-1]["user"]


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
            self.query_prompt_template,
            self.chatgpt_model,
            history,
            user_q,
            self.chatgpt_token_limit - len(user_q)
            )
            # start timing request
            start_keyword = time.perf_counter()

            try: 
                # completion request to openAI

                chat_completion = openai.ChatCompletion.create(
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
                    query_vector_embedding = openai.Embedding.create(
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

            start_cog_search = time.perf_counter()

            if overrides.get("semantic_ranker") and has_text:
                try:
                    r = self.search_client.search(
                        query_text, 
                        filter=filter,
                        query_type=QueryType.SEMANTIC, 
                        query_language= overrides.get("language") or "en-us", 
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
                    r = self.search_client.search(
                        query_text, 
                        filter=filter, 
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
                results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
            else:
                results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
            content = "\n".join(results)

            
            # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
            # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
            prompt_override = overrides.get("prompt_override")
            if prompt_override is None:
                system_message = self.system_message_chat_conversation.format(injected_prompt="")
            elif prompt_override.startswith(">>>"):
                system_message = self.system_message_chat_conversation.format(injected_prompt=prompt_override[3:] + "\n")

            # STEP 3: Generate a contextual and content specific answer using the search results and chat history
            main_llm_req_start = time.perf_counter()

            try:

                messages = self.get_messages_from_history(
                    system_message + "\n\nSources:\n" + content,
                    self.chatgpt_model,
                    history,
                    history[-1]["user"],
                    max_tokens=self.chatgpt_token_limit)

                chat_completion = openai.ChatCompletion.create(
                    deployment_id=self.chatgpt_deployment,
                    model=self.chatgpt_model,
                    messages=messages, 
                    temperature=overrides.get("temperature") or 0.7, 
                    max_tokens=1024, 
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

        msg_to_display = '\n\n'.join([str(message) for message in messages])

        citationList = getCitationObject(chat_content)

        return {"data_points": citationList, "answer": chat_content, "thoughts": f"Searched for:<br>{query_text}<br><br>Conversations:<br>" + msg_to_display.replace('\n', '<br>')}
    
    def get_messages_from_history(self, system_prompt: str, model_id: str, history: Sequence[dict[str, str]], user_conv: str, max_tokens: int = 4096):
        message_builder = MessageBuilder(system_prompt, model_id)

        user_content = user_conv

        message_builder.append_message(self.USER, user_content)

        for h in reversed(history[:-1]):
            if h.get("bot"):
                message_builder.append_message(self.ASSISTANT, h.get('bot'))
            message_builder.append_message(self.USER, h.get('user'))
            if message_builder.token_length > max_tokens:
                break
        
        messages = message_builder.messages
        return messages