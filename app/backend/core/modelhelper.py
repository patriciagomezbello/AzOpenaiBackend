from __future__ import annotations

import tiktoken
import re
from langdetect import detect
import pycountry     
import openai

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

async def cgsIndexColumnFacetDist(client, facet):
    
    try:
        facets_search = await client.search(
                    top=0,
                    skip=0,
                    query_type="simple",
                    select="",
                    search_text="*", 
                    search_fields=[], 
                    filter="", 
                    facets=[facet], 
                    order_by="",
                    include_total_count=True
                )
        res = await facets_search.get_facets()
        return res[facet]
        #return res
    except Exception as e:
        print(e)
        print("setting default to 'de' due to error in facets search query")
        return [{'count': 1, 'value': 'de'}]
    


def getLang(iso_country_code):
    default_lang = {'iso': 'de','name': 'German'}
    if iso_country_code and len(iso_country_code) == 2:
        try:
            language = pycountry.languages.get(alpha_2=iso_country_code)
            return {'iso': iso_country_code, 'name': language.name}
        except Exception as e:
            print('Error evaluating language from alpha 2 iso code - returning default')
            print(e)
            return default_lang
    else:
        print('Returning default due to wrong alpha 2 iso code provided')
        return default_lang


def translateText(text, target_language, chatgpt_deployment):
    prompt = f"Translate the following text to {target_language}:\n\n{text}\n\n"
    messages = [{"role":"system","content":"You are an AI assistant to translate text"},{"role":"user","content":prompt}]
    response = openai.ChatCompletion.create(
        engine=chatgpt_deployment,
        messages = messages,
        temperature=0.0,
        max_tokens=800,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None)
    query_text = response.choices[0].message.content
    return query_text


def replace_abbreviations(string, abbreviations):
    # Create a lower case dictionary for matching 
    lower_abbreviations = {abbrev.lower(): replacement for abbrev, replacement in abbreviations.items()}

    words = string.split()

    for i in range(len(words)):
        word = words[i]
        lower_word = word.lower()

        # Replace words found in the dictionary, ignoring case.
        if lower_word in lower_abbreviations:
            words[i] = lower_abbreviations[lower_word]

        # Handle abbreviations separated by a hyphen
        elif "-" in word and len(word.split("-")) == 2:
            parts = word.split("-")
            lower_parts = lower_word.split("-")
            if lower_parts[0] in lower_abbreviations and lower_parts[1] in lower_abbreviations:
                words[i] = f"{lower_abbreviations[lower_parts[0]]}-{lower_abbreviations[lower_parts[1]]}"
        
        # Handle special characters at the end of a word.
        elif re.search(r"\w[.,!?;]", word): 
            parts = re.split(r"([\.,!?;])", word) 
            replaced_parts = []

            for part in parts[:-1]: # exclude the last element (it's an empty string from splitting at the end character)
                lower_part = part.lower() # use lower case for matching
                if lower_part in lower_abbreviations:
                    replaced_parts.append(lower_abbreviations[lower_part]) # use original dictionary for substitution
                else:
                    replaced_parts.append(part)
            replaced_parts.append(parts[-1]) # add the special char back 
                
            words[i] = "".join(replaced_parts)

    return " ".join(words)





