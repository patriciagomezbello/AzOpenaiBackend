import re
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT") or "mystorageaccount" # ist whrscheinlich unnötig
# to extract the sources cited by the GPT answer according to the prompt instructions
def extractCitedSources(text):
    pattern = r'\[(.*?)\]'
    citationResults = re.findall(pattern, text)
    return citationResults

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
        for i, docName in enumerate(citationResults):
            # Extract the page number from the document name using the getPagePattern
            page = re.search(getPagePattern, docName)
            
            # If a valid page number is found, convert it to an integer and add 1
            if page:
                pageNum = int(page.group(1)) + 1  # real page numbers start with 1, whereas indexing starts with 0
            else:
                pageNum = None  # If no page number is found, set pageNum to None
                
            # Generate the URL for the document on Azure Blob Storage
            url = "https://" + AZURE_STORAGE_ACCOUNT + "blob.core.windows.net/docs/" + docName
            
            # Append a new dictionary (map) to the citationObject list containing the relevant information
            citationObject.append({"positionInText": i, "URL": url, "Page": pageNum})
    
    # Return the list of citationObjects
    return citationObject
