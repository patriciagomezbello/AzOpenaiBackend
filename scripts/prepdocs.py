import os, sys
import platform
import argparse
import glob
import html
import io
import re
import time
import hashlib
import openai
import pdfkit
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image
from pypdf import PdfReader, PdfWriter
from azure.identity import AzureDeveloperCliCredential
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswParameters,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from md2pdf.core import md2pdf

#TODO: check new ms version and adjust


MAX_SECTION_LENGTH = 1100
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100

embTokenLimitPerMinute = 80000

parser = argparse.ArgumentParser(
    description="Prepare documents by extracting content from PDFs, splitting content into sections, uploading to blob storage, and indexing in a search index.",
    epilog="Example: prepdocs.py '..\data\*' --storageaccount myaccount --container mycontainer --searchservice mysearch --index myindex -v"
    )
parser.add_argument("files", help="Files to be processed")
parser.add_argument("--files2convert", help="Files to be processed (in .md format)")
parser.add_argument("--category", help="Value for the category field in the search index for all sections indexed in this run")
parser.add_argument("--skipblobs", action="store_true", help="Skip uploading individual pages to Azure Blob Storage")
parser.add_argument("--storageaccount", help="Azure Blob Storage account name")
parser.add_argument("--container", help="Azure Blob Storage container name")
parser.add_argument("--containerdocs", help="Azure Blob Storage container name for full docs")
parser.add_argument("--storagekey", required=False, help="Optional. Use this Azure Blob Storage account key instead of the current user identity to login (use az login to set current user for Azure)")
parser.add_argument("--tenantid", required=False, help="Optional. Use this to define the Azure directory where to authenticate)")
parser.add_argument("--searchservice", help="Name of the Azure Cognitive Search service where content should be indexed (must exist already)")
parser.add_argument("--openaiservice", help="Name of the Azure OpenAI service used to compute embeddings")
parser.add_argument("--openaideployment", help="Name of the Azure OpenAI model deployment for an embedding model ('text-embedding-ada-002' recommended)")
parser.add_argument("--openaikey", required=False, help="Optional. Use this Azure OpenAI account key instead of the current user identity to login (use az login to set current user for Azure)")
parser.add_argument("--index", help="Name of the Azure Cognitive Search index where content should be indexed (will be created if it doesn't exist)")
parser.add_argument("--searchkey", required=False, help="Optional. Use this Azure Cognitive Search account key instead of the current user identity to login (use az login to set current user for Azure)")
parser.add_argument("--remove", action="store_true", help="Remove references to this document from blob storage and the search index")
parser.add_argument("--removeall", action="store_true", help="Remove all blobs from blob storage and documents from the search index")
parser.add_argument("--localpdfparser", action="store_true", help="Use PyPdf local PDF parser (supports only digital PDFs) instead of Azure Form Recognizer service to extract text, tables and layout from the documents")
parser.add_argument("--formrecognizerservice", required=False, help="Optional. Name of the Azure Form Recognizer service which will be used to extract text, tables and layout from the documents (must exist already)")
parser.add_argument("--formrecognizerkey", required=False, help="Optional. Use this Azure Form Recognizer account key instead of the current user identity to login (use az login to set current user for Azure)")
parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
args = parser.parse_args()

# Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
azd_credential = AzureDeveloperCliCredential() if args.tenantid == None else AzureDeveloperCliCredential(tenant_id=args.tenantid, process_timeout=60)
default_creds = azd_credential if args.searchkey == None or args.storagekey == None else None
search_creds = default_creds if args.searchkey == None else AzureKeyCredential(args.searchkey)
if not args.skipblobs:
    storage_creds = default_creds if args.storagekey == None else args.storagekey
if not args.localpdfparser:
    # check if Azure Form Recognizer credentials are provided
    if args.formrecognizerservice == None:
        print("Error: Azure Form Recognizer service is not provided. Please provide formrecognizerservice or use --localpdfparser for local pypdf parser.")
        exit(1)
    formrecognizer_creds = default_creds if args.formrecognizerkey == None else AzureKeyCredential(args.formrecognizerkey)

if args.openaikey == None:
    openai.api_key = azd_credential.get_token("https://cognitiveservices.azure.com/.default").token
    openai.api_type = "azure_ad"
else:
    openai.api_type = "azure"
    openai.api_key = args.openaikey
openai.api_base = f"https://{args.openaiservice}.openai.azure.com"
openai.api_version = "2022-12-01"

def blob_name_from_file_page(filename, page = 0):
    if os.path.splitext(filename)[1].lower() == ".pdf":
        return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".pdf"
    else:
        return os.path.basename(filename)
    
def upload_blobs_docs(filename):
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.containerdocs)
    if not blob_container.exists():
        blob_container.create_container()
    with open(filename,"rb") as data:
            blob_container.upload_blob(os.path.basename(filename), data, overwrite=True)

def upload_blobs(filename):
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.container)
    if not blob_container.exists():
        blob_container.create_container()
    # if file is PDF split into pages and upload each page as a separate blob
    if os.path.splitext(filename)[1].lower() == ".pdf":
        reader = PdfReader(filename)
        pages = reader.pages
        for i in range(len(pages)):
            blob_name = blob_name_from_file_page(filename, i)
            if args.verbose: print(f"\tUploading blob for page {i} -> {blob_name}")
            f = io.BytesIO()
            writer = PdfWriter()
            writer.add_page(pages[i])
            writer.write(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)
    else:
        blob_name = blob_name_from_file_page(filename)
        with open(filename,"rb") as data:
            blob_container.upload_blob(blob_name, data, overwrite=True)

def remove_blobs(filename):
    if args.verbose: print(f"Removing blobs (from contianer {args.container}) for '{filename or '<all>'}'")
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.container)
    if blob_container.exists():
        if filename == None:
            blobs = blob_container.list_blob_names()
        else:
            prefix = os.path.splitext(os.path.basename(filename))[0]
            blobs = filter(lambda b: re.match(f"{prefix}-\d+\.pdf", b), blob_container.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0]))
        for b in blobs:
            try:
                if args.verbose: print(f"\tRemoving blob {b}")
                blob_container.delete_blob(b)
            except: 
                print (f'not found in {args.container}')

def remove_blobs_docs(filename):
    if args.verbose: print(f"Removing blobs (from contianer {args.containerdocs}) for '{filename}'")
    blob_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(args.containerdocs)
    if blob_container.exists():
        try:
            blob_container.delete_blob(filename)
        except: 
            print (f'not found in {args.containerdocs}')

def table_to_html(table):
    table_html = "<table>"
    rows = [sorted([cell for cell in table.cells if cell.row_index == i], key=lambda cell: cell.column_index) for i in range(table.row_count)]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = "th" if (cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
            cell_spans = ""
            if cell.column_span > 1: cell_spans += f" colSpan={cell.column_span}"
            if cell.row_span > 1: cell_spans += f" rowSpan={cell.row_span}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
        table_html +="</tr>"
    table_html += "</table>"
    return table_html

def get_document_text(filename):
    offset = 0
    page_map = []
    if args.localpdfparser:
        reader = PdfReader(filename)
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    else:
        if args.verbose: print(f"Extracting text from '{filename}' using Azure Form Recognizer")
        form_recognizer_client = DocumentAnalysisClient(endpoint=f"https://{args.formrecognizerservice}.cognitiveservices.azure.com/", credential=formrecognizer_creds, headers={"x-ms-useragent": "azure-search-chat-demo/1.0.0"})
        with open(filename, "rb") as f:
            poller = form_recognizer_client.begin_analyze_document("prebuilt-layout", document = f)
        form_recognizer_results = poller.result()

        for page_num, page in enumerate(form_recognizer_results.pages):
            tables_on_page = [table for table in form_recognizer_results.tables if table.bounding_regions[0].page_number == page_num + 1]

            # mark all positions of the table spans in the page
            page_offset = page.spans[0].offset
            page_length = page.spans[0].length
            table_chars = [-1]*page_length
            for table_id, table in enumerate(tables_on_page):
                for span in table.spans:
                    # replace all table spans with "table_id" in table_chars array
                    for i in range(span.length):
                        idx = span.offset - page_offset + i
                        if idx >=0 and idx < page_length:
                            table_chars[idx] = table_id

            # build page text by replacing charcters in table spans with table html
            page_text = ""
            added_tables = set()
            for idx, table_id in enumerate(table_chars):
                if table_id == -1:
                    page_text += form_recognizer_results.content[page_offset + idx]
                elif not table_id in added_tables:
                    page_text += table_to_html(tables_on_page[table_id])
                    added_tables.add(table_id)

            page_text += " "
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    return page_map

def split_text(page_map):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]
    if args.verbose: print(f"Splitting '{filename}' into sections")

    def find_page(offset):
        l = len(page_map)
        for i in range(l - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return l - 1
    
    for p in page_map:
       # yield (p[2],p[0])
        
        all_text = p[2]
        length = len(all_text)
        start = 0
        end = length
        while start + SECTION_OVERLAP < length:
            last_word = -1
            end = start + MAX_SECTION_LENGTH

            if end > length:
                end = length
            else:
                # Try to find the end of the sentence
                while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                    if all_text[end] in WORDS_BREAKS:
                        last_word = end
                    end += 1
                if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                    end = last_word # Fall back to at least keeping a whole word
            if end < length:
                end += 1

            # Try to find the start of the sentence or at least a whole word boundary
            last_word = -1
            while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
                if all_text[start] in WORDS_BREAKS:
                    last_word = start
                start -= 1
            if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
                start = last_word
            if start > 0:
                start += 1

            section_text = all_text[start:end]
            yield (section_text, p[0]) 

            last_table_start = section_text.rfind("<table")
            if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table")):
                # If the section ends with an unclosed table, we need to start the next section with the table.
                # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
                # If last table starts inside SECTION_OVERLAP, keep overlapping
                if args.verbose: print(f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}")
                start = min(end - SECTION_OVERLAP, start + last_table_start)
            else:
                start = end - SECTION_OVERLAP
            
        if start + SECTION_OVERLAP < end:
            yield (all_text[start:end], p[0])
        

def create_sections(filename, page_map):
    # Loop through the text and page numbers created by split_text function
    for i, (section, pagenum) in enumerate(split_text(page_map)):
        try:
            # Attempt to create an OpenAI Embedding for the input text section
            emb = openai.Embedding.create(engine=args.openaideployment, input=section)
        except Exception as e:
            # If an exception occurs, print the error message
            print(e)
            # Extract any number from the error message
            number = re.search(r'\d+', str(e))
            # Convert the number to integer, if not found, default to 10 seconds
            secondsToWait = int(number.group()) if number else 10
            # Print the wait time
            print(f"Waiting now for {secondsToWait} seconds")
            # Wait for the specified time before trying again
            time.sleep(secondsToWait)
            # Retry creating the OpenAI Embedding for the input section
            emb = openai.Embedding.create(engine=args.openaideployment, input=section)

        # Return a dictionary with the processed section details, like id, content, embedding, etc.
        yield {
            "id": re.sub("[^0-9a-zA-Z_-]", "_", f"{filename}-{i}"),
            "content": section,
            "embedding": emb["data"][0]["embedding"],
            "doclang": None,
            "category": args.category,
            "accesskeys": None,
            "sourcepage": blob_name_from_file_page(filename, pagenum),
            "sourcefile": filename
        }
        

def create_search_index():
    if args.verbose: print(f"Ensuring search index {args.index} exists")
    index_client = SearchIndexClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                     credential=search_creds)
    if args.index not in index_client.list_index_names():
        index = SearchIndex(
            name=args.index,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True),
                SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
                SearchField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                            hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                            vector_search_dimensions=1536, vector_search_configuration="default"),
                SimpleField(name="doclang", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="accesskeys", type="Collection(Edm.String)", filterable=True, retrievable=False),
                SimpleField(name="sourcepage", type="Edm.String", filterable=True, facetable=True),
                SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True)
            ],
            semantic_settings=SemanticSettings(
                configurations=[SemanticConfiguration(
                    name='default',
                    prioritized_fields=PrioritizedFields(
                        title_field=None, prioritized_content_fields=[SemanticField(field_name='content')]))]),
                vector_search=VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default",
                            kind="hnsw",
                            hnsw_parameters=HnswParameters(metric="cosine") 
                        )
                    ]
                )        
            )
        if args.verbose: print(f"Creating {args.index} search index")
        index_client.create_index(index)
    else:
        if args.verbose: print(f"Search index {args.index} already exists")


def index_sections(filename, sections):
    if args.verbose: print(f"Indexing sections from '{filename}' into search index '{args.index}'")
    search_client = SearchClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                    index_name=args.index,
                                    credential=search_creds)
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if args.verbose: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        if args.verbose: print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")

def remove_from_index(filename):
    if args.verbose: print(f"Removing sections from '{filename or '<all>'}' from search index '{args.index}'")
    search_client = SearchClient(endpoint=f"https://{args.searchservice}.search.windows.net/",
                                    index_name=args.index,
                                    credential=search_creds)
    while True:
        filter = None if filename == None else f"sourcefile eq '{os.path.basename(filename)}'"
        r = search_client.search("", filter=filter, top=1000, include_total_count=True)
        if r.get_count() == 0:
            break
        r = search_client.delete_documents(documents=[{ "id": d["id"] } for d in r])
        if args.verbose: print(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)

# Define function to get MD5 hash of a file
def get_md5_hash(file_path):
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
        return file_hash.digest()
    
def invalidFileName(string):
    pattern = r".+-\d+\.pdf$"
    if re.search(pattern, string):
        return True
    return False


def delete_non_pdf_files(files):
    for filename in files:
        if not filename.endswith(".pdf"):
            try:
                file = os.path.dirname(args.files) + '/' + filename 
                os.remove(file)
                print(f"Deleted: {file}")
            except FileNotFoundError:
                print(f"File not found: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")
                sys.exit(99)
                

# delete on pdf files from the data directory first

delete_non_pdf_files(os.listdir(os.path.dirname(args.files)))

# handle data2convert folder to get a unique approach only using pdf files

for filename in glob.glob(args.files2convert):
    file = os.path.splitext(filename)
    target = f"./data/{(file[0].split('/')[2])}.pdf"
    
    # handle markdown
    if file[1] == ".md":
        md2pdf(target,
        md_content=None,
        md_file_path=filename,
        css_file_path=None,
        base_url=None)

    # handle html
    elif file[1] == ".html":
        print(file)
        print(filename)
        print(target)
        pdfkit.from_file(filename, target)

    # handle pictures
    elif file[1] in [".jpg", ".jpeg", ".png"]:
        thecanvas = canvas.Canvas(target, pagesize=A4)
        img = Image.open(filename)
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        canvas_width, canvas_height = A4
        if aspect_ratio > 1:
            # Bild ist breiter als hoch, Skalierung an der Breite orientieren
            img_width = canvas_width
            img_height = int(img_width / aspect_ratio)
        else:
            # Bild ist höher als breit, Skalierung an der Höhe orientieren
            img_height = canvas_height
            img_width = int(img_height * aspect_ratio)
        x = (canvas_width - img_width) / 2
        y = (canvas_height - img_height) / 2
        thecanvas.drawImage(filename, x, y, width=img_width, height=img_height)
        # PDF-Dokument speichern
        thecanvas.save()


# here the code execution starts
if args.removeall:
    remove_blobs(None)
    remove_from_index(None)
else:
    # create index (or not if it already exists)
    create_search_index()

    # init blob in main script for docs comparison
    docs_service = BlobServiceClient(account_url=f"https://{args.storageaccount}.blob.core.windows.net", credential=storage_creds)
    docs_container = docs_service.get_container_client(args.containerdocs)
    if not docs_container.exists():
        docs_container.create_container()

    local_hashmap = {}
    blob_hashmap = {}
    blob_list = docs_container.list_blobs()

    overview = [0,0,0]

    # create md5 byte hashes and add them to hashmaps for comparison
    for filename in glob.glob(args.files):
        local_hashmap[filename] = get_md5_hash(filename)
        if (invalidFileName(filename)):
            raise Exception(f'The filename {filename} is invalid, as it is not allowed to end with -012.pdf etc.')
    for blob in blob_list:
        blob_hashmap[blob.name] = bytes(blob.content_settings.content_md5)

    # loop through local files
    for filename, local_hash in local_hashmap.items():

        # check if the file is in the blob
        if os.path.basename(filename) in blob_hashmap:
            # if true, get the hash and then compare
            remote_hash = blob_hashmap[os.path.basename(filename)]
            if local_hash != remote_hash:
                # different hashes, upload file again
                try:
                    print (f'{filename} changed, will be processed again')
                    upload_blobs(filename)
                    upload_blobs_docs(filename)
                    page_map = get_document_text(filename)
                    sections = create_sections(os.path.basename(filename), page_map)
                    index_sections(os.path.basename(filename), sections)
                    overview[0] += 1
                except Exception as e:
                    print("something went wrong, clearing up state now")
                    print("Error:", e)
                    remove_blobs(filename)
                    remove_blobs_docs(filename)
                    remove_from_index(filename)
                    break

        else:
            try:
                # only in local, upload file
                print (f'{filename} only local, will be processed')
                upload_blobs(filename)
                upload_blobs_docs(filename)
                page_map = get_document_text(filename)
                sections = create_sections(os.path.basename(filename), page_map)
                index_sections(os.path.basename(filename), sections)
                overview[1] += 1
            except Exception as e:
                print("something went wrong, clearing up state now")
                print("Error:", e)
                remove_blobs(filename)
                remove_blobs_docs(filename)
                remove_from_index(filename)
                break

    # loop through blob files
    for filename in blob_hashmap:
        if platform.system() == 'Windows':
            filename_check = f'./data\\{filename}'
        else:
            filename_check = f'./data/{filename}'
            
        if filename_check not in local_hashmap:
            # only in remote, remove file
            try:
                print (f'{filename} only remote, will be removed from blob and index')
                remove_blobs(filename)
                remove_blobs_docs(filename)
                remove_from_index(filename)
                overview[2] += 1
            except Exception as e:
                print("something went wrong with the deletion of files, please contact the Azure Team")
                print("Error:", e)
                break
    print (f'{str(overview[0])} files were changed, {str(overview[1])} files were added, {str(overview[2])} files were deleted')
