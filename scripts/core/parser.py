import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--files", help="Files to be processed pdfs")
parser.add_argument("--files2convert", help="Files to be converted to pdfs)")
parser.add_argument("--storageaccount", help="Azure Blob Storage account name")
parser.add_argument("--containerdocs", help="Azure Blob Storage container for docs")
parser.add_argument(
    "--containerdata",
    help="Azure Blob Storage container for data, will be synced with docs container",
)
parser.add_argument("--storagekey", required=False)
parser.add_argument("--tenantid", required=False, help="Optional")
parser.add_argument("--searchservice", help="Name of Azure AI Search service")
parser.add_argument("--openaiservice", help="Name of OpenAI service")
parser.add_argument(
    "--openaideployment",
    help="Name of the Azure OpenAI model deployment for an embedding model ('text-embedding-ada-002' recommended)",
)
parser.add_argument("--openaikey", required=False, help="Optional")
parser.add_argument(
    "--index",
    help="Name of the Azure AI Search index where content should be indexed (will be created if it doesn't exist)",
)
parser.add_argument("--searchkey", required=False, help="Optional")
parser.add_argument(
    "--removeall",
    action="store_true",
    help="Remove all blobs from blob storage and documents from the search index",
)
parser.add_argument(
    "--localpdfparser",
    action="store_true",
    help="Use PyPdf local PDF parser (supports only digital PDFs) instead of Azure Form Recognizer service",
)
parser.add_argument(
    "--formrecognizerservice",
    required=False,
    help="Optional. Name of the Azure Form Recognizer service which will be used to extract text,  \
        tables and layout from the documents (must exist already)",
)
parser.add_argument(
    "--formrecognizerkey",
    required=False,
    help="Optional",
)

parser.add_argument("--data_mode", required=True)
parser.add_argument("--data_conversion", required=True)
parser.add_argument("--file_mode", required=True)
parser.add_argument("--lc_mode", required=True)
parser.add_argument("--reset_index")
parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
