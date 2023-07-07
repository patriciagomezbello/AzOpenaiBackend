import openai
import json
import os
import time
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, Vector
from approaches.approach import Approach
from text import nonewlines
from approaches.token import addTokenCount
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler

global ENVIRONMENT
ENVIRONMENT = os.environ.get("SERVER_ENVIRONMENT") or "remote"


# Chat-read-retrieve-read implementation, using the Cognitive Search and OpenAI APIs directly. It first retrieves
# top documents from search, then constructs a prompt with them, and then uses OpenAI to generate an completion 
# (answer) with that prompt.

class ChatReadRetrieveReadApproach(Approach):
    
    #TODO: implement try except finally for have logging also in case of timeouts

    global r_dec
    r_dec = 3

    if ENVIRONMENT == "remote":
        logger = logging.getLogger(__name__)
        logger.addHandler(AzureLogHandler())
    else:
        logger = ""

    # initialize empty config variables to satisfy linter
    main_prefix, sources_prefix, end_postfix, keyword_prefix, chat_history_prefix, question_prefix, question_postfix = "", "", "", "", "", "", ""

    # Load the JSON config file for the context
    with open('./context.json', 'r') as f:
        data = json.load(f)

    # Create variables from the keys and values in the JSON object to establish the context
    for key, value in data.items():
        globals()[key] = value

    # initialize string with fixed context variables in f"" string and formatable string in brackets only
    prompt_prefix = f"{main_prefix}\n" + "{injected_prompt}\n" + f"{sources_prefix}\n" + "{sources}\n" +f"{end_postfix}"+ "{chat_history}"
    query_prompt_template = f"{keyword_prefix}\n{chat_history_prefix}\n" + "{chat_history}\n" +f"{question_prefix}\n" + "{question}\n" + f"{question_postfix}"

    # init function for the extended approach class for crrr
    def __init__(self, search_client: SearchClient, chatgpt_deployment: str, gpt_deployment: str, embedding_deployment: str, sourcepage_field: str, content_field: str):
        self.search_client = search_client
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt_deployment = gpt_deployment
        self.embedding_deployment = embedding_deployment
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
    
    # executable function that is connected to the chat api -> receives and responds like chatgpt but with enterprise data‚
    def run(self, history: list[dict], overrides: dict) -> any:
        
        #start logging full request time
        start_chat = time.perf_counter()
        
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top") or 3
        exclude_category = overrides.get("exclude_category") or None
        filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None

        usedTokens: dict = {}

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        prompt = self.query_prompt_template.format(chat_history=self.get_chat_history_as_text(history, include_last_turn=False), question=history[-1]["user"])
        
        # start timing request
        start_keyword = time.perf_counter()

        # completion request to openAI
        completion = openai.Completion.create(
            engine=self.chatgpt_deployment, 
            prompt=prompt, 
            temperature=0.0, 
            max_tokens=32, 
            n=1, 
            stop=["\n"])
        query_text = completion.choices[0].text

        # save time for completion request for keyword optimization and add token count to request token object
        keyword_request_time = round(time.perf_counter() - start_keyword, r_dec)

        addTokenCount(usedTokens, completion)

        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
        # If retrieval mode includes vectors, compute an embedding for the query
        if overrides.get("retrieval_mode") in ["vectors", "hybrid", None]:

            start_embedding = time.perf_counter()

            query_vector_embedding = openai.Embedding.create(
                engine=self.embedding_deployment, 
                input=query_text)
            query_vector = query_vector_embedding.data[0].embedding

            embedding_request_time = round(time.perf_counter() - start_embedding, r_dec)

            addTokenCount(usedTokens, query_vector_embedding)

        else:
            query_vector = None

        # Only keep the text query if the retrieval mode uses text, otherwise drop it
        if overrides.get("retrieval_mode") == "vectors":
            query_text = None

        start_cog_search = time.perf_counter()

        if overrides.get("semantic_ranker"):
            r = self.search_client.search(query_text, 
                                          filter=filter,
                                          query_type=QueryType.SEMANTIC, 
                                          query_language= overrides.get("language") or "en-us", 
                                          query_speller="lexicon", 
                                          semantic_configuration_name="default", 
                                          top=top, 
                                          query_caption="extractive|highlight-false" if use_semantic_captions else None,
                                          vector=Vector(value=query_vector, k=50, fields="embedding") if query_vector else None)
        else:
            r = self.search_client.search(query_text, filter=filter, top=top, vector=Vector(value=query_vector, k=50, fields="embedding") if query_vector else None)
        
        cog_search_request_time = round(time.perf_counter() - start_cog_search, r_dec)
        
        if use_semantic_captions:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(" . ".join([c.text for c in doc['@search.captions']])) for doc in r]
        else:
            results = [doc[self.sourcepage_field] + ": " + nonewlines(doc[self.content_field]) for doc in r]
        content = "\n".join(results)

        
        # Allow client to replace the entire prompt, or to inject into the exiting prompt using >>>
        prompt_override = overrides.get("prompt_template")
        if prompt_override is None or prompt_override == "":
            prompt = self.prompt_prefix.format(injected_prompt="", sources=content, chat_history=self.get_chat_history_as_text(history))
        elif prompt_override.startswith(">>>"):
            prompt = self.prompt_prefix.format(injected_prompt=prompt_override[3:] + "\n", sources=content, chat_history=self.get_chat_history_as_text(history))
        else:
            prompt = prompt_override.format(sources=content, chat_history=self.get_chat_history_as_text(history))

        # STEP 3: Generate a contextual and content specific answer using the search results and chat history
        main_llm_req_start = time.perf_counter()

        completion = openai.Completion.create(
            engine=self.chatgpt_deployment, 
            prompt=prompt, 
            temperature=overrides.get("temperature") or 0.7, 
            max_tokens=1024, 
            n=1, 
            stop=["<|im_end|>", "<|im_start|>"])
        
        main_llm_req_time = round(time.perf_counter() - main_llm_req_start, r_dec)

        addTokenCount(usedTokens, completion)

        chat_time = round(time.perf_counter() - start_chat, r_dec)

        properties = {"custom_dimensions": {
                          "usedTokens": usedTokens,
                          "full_chat_time": chat_time, 
                          "keyword_opt_time": keyword_request_time,
                          "embedding_time": embedding_request_time or 0,
                          "search_time": cog_search_request_time,
                          "main_req_time": main_llm_req_time
                          }
                        }
        
        #TODO: fix logging for local and remote setup
        #if ENVIRONMENT == "remote":
        # Use properties in logging statements
        #logger.warning('action', extra=properties)

        print(properties)

        return {"data_points": results, "answer": completion.choices[0].text, "thoughts": f"Searched for:<br>{query_text}<br><br>Prompt:<br>" + prompt.replace('\n', '<br>')}
    
    def get_chat_history_as_text(self, history, include_last_turn=True, approx_max_tokens=1000) -> str:
        history_text = ""
        for h in reversed(history if include_last_turn else history[:-1]):
            history_text = """<|im_start|>user""" +"\n" + h["user"] + "\n" + """<|im_end|>""" + "\n" + """<|im_start|>assistant""" + "\n" + (h.get("bot") + """<|im_end|>""" if h.get("bot") else "") + "\n" + history_text
            if len(history_text) > approx_max_tokens*4:
                break    
        return history_text