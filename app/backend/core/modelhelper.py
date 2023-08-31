from __future__ import annotations

import tiktoken
import re
from langdetect import detect

MODELS_2_TOKEN_LIMITS = {
    "gpt-35-turbo": 4000,
    "gpt-3.5-turbo": 4000,
    "gpt-35-turbo-16k": 16000,
    "gpt-3.5-turbo-16k": 16000,
    "gpt-4": 8100,
    "gpt-4-32k": 32000
}

AOAI_2_OAI = {
    "gpt-35-turbo": "gpt-3.5-turbo",
    "gpt-35-turbo-16k": "gpt-3.5-turbo-16k"
}


def get_token_limit(model_id: str) -> int:
    if model_id not in MODELS_2_TOKEN_LIMITS:
        raise ValueError("Expected model gpt-35-turbo and above")
    return MODELS_2_TOKEN_LIMITS[model_id]


def num_tokens_from_messages(message: dict[str, str], model: str) -> int:
    """
    Calculate the number of tokens required to encode a message.
    Args:
        message (dict): The message to encode, represented as a dictionary.
        model (str): The name of the model to use for encoding.
    Returns:
        int: The total number of tokens required to encode the message.
    Example:
        message = {'role': 'user', 'content': 'Hello, how are you?'}
        model = 'gpt-3.5-turbo'
        num_tokens_from_messages(message, model)
        output: 11
    """
    encoding = tiktoken.encoding_for_model(get_oai_chatmodel_tiktok(model))
    num_tokens = 2  # For "role" and "content" keys
    for key, value in message.items():
        num_tokens += len(encoding.encode(value))
    return num_tokens


def get_oai_chatmodel_tiktok(aoaimodel: str) -> str:
    message = "Expected Azure OpenAI ChatGPT model name"
    if aoaimodel == "" or aoaimodel is None:
        raise ValueError(message)
    if aoaimodel not in AOAI_2_OAI and aoaimodel not in MODELS_2_TOKEN_LIMITS:
        raise ValueError(message)
    return AOAI_2_OAI.get(aoaimodel) or aoaimodel


def addTokenCount(tokenDict: dict, res: dict):
    """Adds the tokens of a OpenAI Response to a dict"""
    if res.model in tokenDict:
        tokenDict[res.model] += res.usage.total_tokens
    else:
        tokenDict[res.model] = res.usage.total_tokens


# to extract the sources cited by the GPT answer according to the prompt instructions
def extractCitedSources(text):
    pattern = r'\[(.*?)\]'
    citationResults = re.findall(pattern, text)
    return citationResults

def filter_duplicates(list_of_dicts):
    unique_values = set()
    filtered_list = []
    for d in list_of_dicts:
        if (d['docName'], d['page']) not in unique_values:
            unique_values.add((d['docName'], d['page']))
            filtered_list.append(d)
    return filtered_list

# Define a function to extract citation information from a given text
# In this function, getCitationObject takes a text input and extracts citation information, creating a list of dictionaries containing information about each citation, such as its position in the text, URL, and associated page number.
def getCitationObject(text):
    # Initialize an empty list to store citation objects
    citationObject = []
    # Define a regular expression pattern to match citations within square brackets
    pattern = r'\[(.*?)\]'
    # Find all matching citations in the text using the pattern
    citationResults = re.findall(pattern, text)
    
    # Check if there are any citation results found in the text
    if len(citationResults) > 0:
        # Define a regular expression pattern to extract the page number from the document name
        getPagePattern = r"-([0-9]+)(?:-\d)?\."
        
        # Loop through the citations found in the text
        # the "i" must stay !!!!!
        for i, docName in enumerate(citationResults):
            # Extract the page number from the document name using the getPagePattern

            page = re.search(getPagePattern, docName)
            
            # If a valid page number is found, convert it to an integer and add 1
            if page:
                pageNum = int(page.group(1)) + 1  # real page numbers start with 1, whereas indexing starts with 0
            else:
                pageNum = None  # If no page number is found, set pageNum to None

            # Append a new dictionary (map) to the citationObject list containing the relevant information
            citationObject.append({"docName": re.sub(r'-\d+.pdf', '.pdf', docName), "page": pageNum})


    f_citationObject = filter_duplicates(citationObject)
    # Return the list of citationObjects
    return f_citationObject

def detectLang(text, defaultLang='de'):
    try:
        ret = detect(text)
        return ret
    except Exception as e:
        print(e)
        return defaultLang





