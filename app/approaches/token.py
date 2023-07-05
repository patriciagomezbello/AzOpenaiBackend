import tiktoken

available_encodings = ["p50k_base", "cl100k_base", "r50k_base"]
available_models    = ["gpt-4", "gpt-3.5-turbo", "text-embedding-ada-002", "davinci"]


def num_tokens(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    if encoding_name in available_encodings:
        encoding = tiktoken.get_encoding_for_model(encoding_name)
    elif encoding_name in available_models:
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