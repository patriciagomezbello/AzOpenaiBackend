import re
# to extract the sources cited by the GPT answer according to the prompt instructions
def extractCitedSources(text):
    pattern = r'\[(.*?)\]'
    citationResults = re.findall(pattern, text)
    return citationResults