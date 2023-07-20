import re
import tiktoken

available_encodings = ["p50k_base", "cl100k_base", "r50k_base"]
available_models    = ["gpt-4", "gpt-35-turbo", "text-embedding-ada-002", "davinci"]

def num_tokens(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    if encoding_name in available_models:
        encoding = tiktoken.get_encoding_for_model(encoding_name)
    elif encoding_name in available_encodings:
        encoding = tiktoken.get_encoding(encoding_name)
    else:
        return -1
    
    num_tokens = len(encoding.encode(string))
    return num_tokens

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

import re

def replaceCitations(text, sources):
# A dictionary to store the source mappings
    source_mapping = {}

# A counter to generate unique replacement numbers
    num = 1

    # Loop through the sources in the text
    for source in re.findall(r'\[(.*?)\]', text):
        # Extract the docName and page from the source string
        docName = re.sub(r'-\d+.pdf', '.pdf', source)

        match1 = re.search(r'(?:.*-)(\d+)\.pdf', source)

        if match1:
            page = int(match1.group(1)) + 1
        else:
            page = 0

        # Look for a matching source in the list
        match = next((x for x in sources if x["docName"] == docName and x["page"] == int(page)), None)

        # If there's a match, add it to the mapping
        if match:
            key = (match["docName"], match["page"])
            if key in source_mapping:
                source_num = source_mapping[key]
            else:
                source_num = num
                num += 1
                source_mapping[key] = source_num
            # Replace the source with the number
            text = text.replace("[{}]".format(source), "[{}]".format(source_num))
    return text
