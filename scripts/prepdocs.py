import os
import argparse
import time
import openai
from lingua import Language, LanguageDetectorBuilder
from azure.identity import AzureDeveloperCliCredential
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from core.aisearch import (
    create_search_index,
    index_sections,
    remove_from_index,
    create_embedding,
)
from core.helper import (
    check_time,
    delete_non_pdf_files,
    detectLang,
    file_path_to_id,
    get_md5_hash,
    invalidFileName,
    name_from_path,
    url_to_id,
)
from core.document import get_document_text, split_text
from core.convert import convert_files
from core.blob import blob_name_from_file_page, upload_blobs_docs, remove_blobs_docs
from core.langchain import split_langchain_text


MAX_SECTION_LENGTH = int(os.getenv("MAX_SECTION_LENGTH", 1100))
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100


# build languages for usage
detector = LanguageDetectorBuilder.from_languages(
    Language.ENGLISH,
    Language.GERMAN,
    Language.HUNGARIAN,
    Language.CROATIAN,
    Language.SLOVAK,
    Language.RUSSIAN,
    Language.CZECH,
    Language.GREEK,
    Language.PUNJABI,
    Language.PORTUGUESE,
    Language.POLISH,
    Language.CZECH,
    Language.SPANISH,
    Language.SERBIAN,
    Language.AFRIKAANS,
    Language.ALBANIAN,
    Language.BULGARIAN,
    Language.FRENCH,
    Language.PORTUGUESE,
    Language.ROMANIAN,
    Language.MACEDONIAN,
    Language.HINDI,
    Language.DUTCH,
    Language.DANISH,
    Language.ITALIAN,
    Language.CHINESE,
    Language.MALAY,
    Language.BOSNIAN,
).build()


def create_document_sections(file_path, page_map, accessKeys, category=None):
    file_id = file_path_to_id(file_path)
    # Loop through the text and page numbers created by split_text function

    file = name_from_path(file_path=file_path, files_directory=args.files)

    for i, (section, pagenum) in enumerate(
        split_text(
            page_map=page_map,
            file_path=file_path,
            max_section_length=MAX_SECTION_LENGTH,
            section_overlap=SECTION_OVERLAP,
            sentence_search_limit=SENTENCE_SEARCH_LIMIT,
            verbose=args.verbose,
        )
    ):
        # Attempt to create an OpenAI Embedding for the input text section
        emb = create_embedding(engine=args.openaideployment, input=section)

        # Return a dictionary with the processed section details, like id, content, embedding, etc.
        yield {
            "id": f"{file_id}-page-{i}",
            "content": section,
            "embedding": emb["data"][0]["embedding"],
            "doclang": detectLang(text=section, detector=detector),
            "category": category,
            "accesskeys": accessKeys,
            "sourcepage": blob_name_from_file_page(
                file_path=file_path, files_directory=args.files, page=pagenum
            ),
            "sourcefile": file,
        }


def create_langchain_sections(document_map, accessKeys, category=None):
    # file_id = file_path_to_id(file_path)
    # # Loop through the text and page numbers created by split_text function

    # file = name_from_path(file_path=file_path, files_directory=args.files)
    counter = 0
    for i, (section, source, title) in enumerate(
        split_langchain_text(
            document_map=document_map,
            max_section_length=MAX_SECTION_LENGTH,
            section_overlap=SECTION_OVERLAP,
            sentence_search_limit=SENTENCE_SEARCH_LIMIT,
        )
    ):
        id = url_to_id(source, counter)
        # Attempt to create an OpenAI Embedding for the input text section
        emb = create_embedding(engine=args.openaideployment, input=section)

        counter = counter + 1

        # Return a dictionary with the processed section details, like id, content, embedding, etc.
        yield {
            "id": id,
            "content": section,
            "embedding": emb["data"][0]["embedding"],
            "doclang": detectLang(text=section, detector=detector),
            "category": category,
            "accesskeys": accessKeys,
            "sourcepage": source,
            "sourcefile": title,
        }


# SCRIPT EXECUTION BEGINS

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare documents by extracting content from PDFs, splitting content into sections,  \
            uploading to blob storage, and indexing in a search index.",
    )
    parser.add_argument("files", help="Files to be processed pdfs")
    parser.add_argument("--files2convert", help="Files to be converted to pdfs)")
    parser.add_argument("--storageaccount", help="Azure Blob Storage account name")
    parser.add_argument("--containerdocs", help="Azure Blob Storage container for docs")
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
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    def get_credentials(
        searchkey=args.searchkey,
        storagekey=args.storagekey,
        tenantid=args.tenantid,
        localpdfparser=args.localpdfparser,
        formrecognizerservice=args.formrecognizerservice,
        formrecognizerkey=args.formrecognizerkey,
        openaiservice=args.openaiservice,
        openaikey=args.openaikey,
    ):
        # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
        azd_credential = (
            AzureDeveloperCliCredential()
            if tenantid is None
            else AzureDeveloperCliCredential(tenant_id=tenantid, process_timeout=60)
        )
        default_creds = (
            azd_credential if searchkey is None or storagekey is None else None
        )
        search_creds = (
            default_creds if searchkey is None else AzureKeyCredential(searchkey)
        )
        storage_creds = default_creds if storagekey is None else storagekey
        if not localpdfparser:
            # check if Azure Form Recognizer credentials are provided
            if formrecognizerservice is None:
                print(
                    "Error: Azure Form Recognizer service is not provided. Please provide formrecognizerservice  \
                        or use --localpdfparser for local pypdf parser."
                )
                exit(1)
            formrecognizer_creds = (
                default_creds
                if formrecognizerkey is None
                else AzureKeyCredential(formrecognizerkey)
            )

        if openaikey is None:
            openai.api_key = azd_credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token
            openai.api_type = "azure_ad"
        else:
            openai.api_type = "azure"
            openai.api_key = openaikey
        openai.api_base = f"https://{openaiservice}.openai.azure.com"
        openai.api_version = "2022-12-01"
        return (
            search_creds,
            storage_creds,
            default_creds,
            azd_credential,
            formrecognizer_creds,
            openai.api_type,
            openai.api_key,
            openai.api_base,
            openai.api_version,
        )

    # Take the start time
    start_time = time.time()
    # get credentials
    (
        search_creds,
        storage_creds,
        default_creds,
        azd_credential,
        formrecognizer_creds,
        openai.api_type,
        openai.api_key,
        openai.api_base,
        openai.api_version,
    ) = get_credentials()

    # delete non pdf files from data
    delete_non_pdf_files(args.files)

    # FILE CONVERTION BEGINS
    DATA_CONVERT = True

    pdfkit_options = {"encoding": "UTF-8"}

    if DATA_CONVERT:
        convert_files(folder=args.files2convert)

    # INDEX HANDLING BEGINS
    if args.removeall:
        remove_from_index(
            file_path=None,
            index_name=args.index,
            search_creds=search_creds,
            searchservice=args.searchservice,
            file_directory=args.files,
            verbose=args.verbose,
        )
    else:
        # create index (or not if it already exists)
        create_search_index(
            index_name=args.index,
            search_creds=search_creds,
            searchservice=args.searchservice,
            verbose=args.verbose,
        )

        # init blob in main script for docs comparison
        docs_service = BlobServiceClient(
            account_url=f"https://{args.storageaccount}.blob.core.windows.net",
            credential=storage_creds,
        )
        docs_container = docs_service.get_container_client(args.containerdocs)
        if not docs_container.exists():
            docs_container.create_container()

        local_hashmap = {}
        blob_hashmap = {}
        blob_list = docs_container.list_blobs()

        overview = [0, 0, 0]

        # loop through all files in args.files (should be 'data')
        # creates a local hashmap that has an array with the file_path 'data/example.pdf',
        # md5hash and category that is the first folder after the args.files

        for root, dirs, files in os.walk(args.files):
            for file in files:
                file_path = os.path.join(root, file)
                sp_path = file_path.split("/")
                category = sp_path[1] if (sp_path[1] != file) else None

                local_hashmap[
                    name_from_path(file_path=file_path, files_directory=args.files)
                ] = [
                    file_path,
                    get_md5_hash(file_path),
                    category,
                ]
                if invalidFileName(file):
                    raise Exception(
                        f"The filename {file} is invalid, as it is not allowed to end with -012.pdf etc."
                    )

        # creation of the blob hashmap with the blob.name (file_name) and the md5hash as value
        for blob in blob_list:
            blob_hashmap[blob.name] = bytes(blob.content_settings.content_md5)

        # loop through local files
        print("go through files locally")

        # every local file of the hashmap will be processed, local_data is the array of values of the hashmap
        for file, local_data in local_hashmap.items():
            if check_time(start_time):
                print("Refreshing credentials")
                (
                    search_creds,
                    storage_creds,
                    default_creds,
                    azd_credential,
                    formrecognizer_creds,
                    openai.api_type,
                    openai.api_key,
                    openai.api_base,
                    openai.api_version,
                ) = get_credentials()
                start_time = time.time()
            # get category and file_path
            local_category = local_data[2]
            file_path_local = local_data[0]

            # check if the file is in the blob
            if file in blob_hashmap:
                # if true, get the hash and category for comparison
                remote_hash = blob_hashmap[file]
                # remote_category = get_search_value(file=file,key="category")

                # check if the hashes are the same, if not, file will be upserted, no else case, only elif for category
                if local_data[1] != remote_hash:
                    try:
                        print(f"{file} changed, will be processed again")
                        upload_blobs_docs(
                            file_path=file_path_local,
                            files_directory=args.files,
                            storageaccount=args.storageaccount,
                            storage_creds=storage_creds,
                            containerdocs=args.containerdocs,
                        )

                        page_map = get_document_text(
                            file_path=file_path_local,
                            formrecognizer_creds=formrecognizer_creds,
                            formrecognizerservice=args.formrecognizerservice,
                            localpdf=args.localpdfparser,
                            verbose=args.verbose,
                        )

                        sections = create_document_sections(
                            file_path_local, page_map, ["All"], local_category
                        )

                        index_sections(
                            index_name=args.index,
                            searchservice=args.searchservice,
                            search_creds=search_creds,
                            file=file,
                            sections=sections,
                        )

                        overview[0] += 1
                    except Exception as e:
                        print("something went wrong, clearing up state now")
                        print("Error:", e)
                        remove_blobs_docs(
                            file_path=file_path_local,
                            files_directory=args.files,
                            containerdocs=args.containerdocs,
                            storageaccount=args.storageaccount,
                            storage_creds=storage_creds,
                            verbose=args.verbose,
                        )
                        remove_from_index(
                            file_path=file_path_local,
                            index_name=args.index,
                            search_creds=search_creds,
                            searchservice=args.searchservice,
                            file_directory=args.files,
                            verbose=args.verbose,
                        )
                        break
                # if the categories are not similar, exchange the category value in index
                # elif local_category != remote_category:
                #    update_search_value(file=file, key="category",value=local_category)

            # this happens when file is not in blob
            else:
                try:
                    # only in local, upload file
                    print(f"{file} only local, will be processed")
                    upload_blobs_docs(
                        file_path=file_path_local,
                        files_directory=args.files,
                        storageaccount=args.storageaccount,
                        storage_creds=storage_creds,
                        containerdocs=args.containerdocs,
                    )

                    page_map = get_document_text(
                        file_path=file_path_local,
                        formrecognizer_creds=formrecognizer_creds,
                        formrecognizerservice=args.formrecognizerservice,
                        localpdf=args.localpdfparser,
                        verbose=args.verbose,
                    )

                    sections = create_document_sections(
                        file_path_local, page_map, ["All"], local_category
                    )

                    index_sections(
                        file=file,
                        index_name=args.index,
                        search_creds=search_creds,
                        searchservice=args.searchservice,
                        sections=sections,
                    )

                    overview[1] += 1
                except Exception as e:
                    print("something went wrong, clearing up state now")
                    print("Error:", e)
                    remove_blobs_docs(
                        file_path=file_path_local,
                        files_directory=args.files,
                        containerdocs=args.containerdocs,
                        storageaccount=args.storageaccount,
                        storage_creds=storage_creds,
                        verbose=args.verbose,
                    )
                    remove_from_index(
                        file_path=file_path_local,
                        index_name=args.index,
                        search_creds=search_creds,
                        searchservice=args.searchservice,
                        file_directory=args.files,
                        verbose=args.verbose,
                    )
                    break

        # loop through blob files
        print("go through files in blob")
        for file in blob_hashmap:
            if file not in local_hashmap:
                # only in remote, remove file
                try:
                    print(f"{file} only remote, will be removed from blob and index")
                    remove_blobs_docs(
                        file_path=file,
                        files_directory=args.files,
                        containerdocs=args.containerdocs,
                        storageaccount=args.storageaccount,
                        storage_creds=storage_creds,
                        verbose=args.verbose,
                        isPath=False,
                    )
                    remove_from_index(
                        file_path=file,
                        isPath=False,
                        index_name=args.index,
                        search_creds=search_creds,
                        searchservice=args.searchservice,
                        file_directory=args.files,
                        verbose=args.verbose,
                    )
                    overview[2] += 1
                except Exception as e:
                    print(
                        "something went wrong with the deletion of files, please contact the Azure Team"
                    )
                    print("Error:", e)
                    break
        print(
            f"{str(overview[0])} files were changed, {str(overview[1])} files were added,  \
{str(overview[2])} files were deleted"
        )
