import asyncio
import json
import os
import time
from typing import cast
from typing import Optional
from urllib.parse import quote

import nest_asyncio
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential
from azure.identity.aio import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider
from azure.storage.blob import BlobServiceClient
from core.aisearch import cleanup_lc_corpses_from_index
from core.aisearch import cleanup_lc_sections_from_index
from core.aisearch import create_embedding
from core.aisearch import create_search_index
from core.aisearch import delete_search_index
from core.aisearch import index_sections
from core.aisearch import remove_file_from_index
from core.aisearch import remove_lc_from_index
from core.aisearch import update_roles_index
from core.blob import blob_name_from_blob_page
from core.blob import blob_name_from_file_page
from core.blob import remove_all_blobs_from_container
from core.blob import remove_blobs_docs
from core.blob import upload_blobs_docs
from core.convert import convert_files
from core.document import get_document_text
from core.document import get_document_text_from_blob
from core.document import split_text
from core.helper import check_time
from core.helper import delete_non_pdf_files
from core.helper import detectLang
from core.helper import file_path_to_id
from core.helper import get_md5_hash
from core.helper import invalidFileName
from core.helper import name_from_path
from core.helper import url_to_id
from core.langchain import handle_lc_config_item
from core.langchain import split_langchain_text
from core.langchain import split_langchain_text_recursive
from core.parser import parser
from lingua import Language
from lingua import LanguageDetector
from lingua import LanguageDetectorBuilder
from openai import AsyncAzureOpenAI

# fixes a bug with asyncio and jupyter

nest_asyncio.apply()

role_config: Optional[dict[Optional[str], list[str]]] = None

try:
    with open("role_config.json", "r") as file:
        role_config = cast(dict[Optional[str], list[str]], json.load(file))
        role_config.update({None: ["public"]})
except OSError:
    print("---> no role_config found, no roles added to search index")
    role_config = {None: ["public"]}

MAX_SECTION_LENGTH: int = int(os.getenv("MAX_SECTION_LENGTH", 1100))
SENTENCE_SEARCH_LIMIT: int = 100
SECTION_OVERLAP: int = 100


# build languages for usage
detector: LanguageDetector = LanguageDetectorBuilder.from_languages(
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


async def create_document_sections(openai_client: AsyncAzureOpenAI, file_path, page_map, category=None):
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
        emb = await create_embedding(client=openai_client, engine=args.openaideployment, input=section)

        if emb is not None:
            if category is None or role_config is None:
                roles = ["public"]
            else:
                roles = role_config.get(category, ["public"])
            # Return a dictionary with the processed section details, like id, content, embedding, etc.
            yield {
                "id": f"{file_id}-page-{i}",
                "content": section,
                "embedding": emb.data[0].embedding,
                "doclang": detectLang(text=section, detector=detector),
                "category": category,
                "roles": roles,
                "sourcepage": blob_name_from_file_page(file_path=file_path, files_directory=args.files, page=pagenum),
                "sourcefile": file,
            }
        else:
            raise ValueError("No embedding was created")


async def create_document_blob_sections(openai_client: AsyncAzureOpenAI, blob_name, page_map, category=None):
    blob_id = file_path_to_id(blob_name)
    # Loop through the text and page numbers created by split_text function

    for i, (section, pagenum) in enumerate(
        split_text(
            page_map=page_map,
            file_path=blob_name,
            max_section_length=MAX_SECTION_LENGTH,
            section_overlap=SECTION_OVERLAP,
            sentence_search_limit=SENTENCE_SEARCH_LIMIT,
            verbose=args.verbose,
        )
    ):
        # Attempt to create an OpenAI Embedding for the input text section
        emb = await create_embedding(client=openai_client, engine=args.openaideployment, input=section)
        if emb is not None:
            # Return a dictionary with the processed section details, like id, content, embedding, etc.

            if category is None or role_config is None:
                roles = ["public"]
            else:
                roles = role_config.get(category, ["public"])
            yield {
                "id": f"{blob_id}-page-{i}",
                "content": section,
                "embedding": emb.data[0].embedding,
                "doclang": detectLang(text=section, detector=detector),
                "category": category,
                "roles": roles,
                "sourcepage": blob_name_from_blob_page(blob_name, page=pagenum),
                "sourcefile": blob_name,
            }
        else:
            raise ValueError("No embedding was created")


async def create_langchain_sections(
    openai_client: AsyncAzureOpenAI,
    document_map,
    search_creds,
    splitter="standard",
    category=None,
):
    # define dictionary with source as key and number (counter) as value
    counter_dict: dict[str, int] = {}

    # define list of indexed sources for corpse finding
    indexed_sources: list[str] = []
    base = document_map[0][1]  # get the base url for the document

    for _, (source, base, section) in enumerate(
        split_langchain_text(
            document_map=document_map,
            max_section_length=MAX_SECTION_LENGTH,
            section_overlap=SECTION_OVERLAP,
            sentence_search_limit=SENTENCE_SEARCH_LIMIT,
        )
        if splitter == "standard"
        else split_langchain_text_recursive(
            document_map=document_map,
            max_section_length=MAX_SECTION_LENGTH,
            section_overlap=SECTION_OVERLAP,
        )
    ):
        # check if key already exists, if not initilaize with zero

        id = url_to_id(source, counter_dict)

        # Attempt to create an OpenAI Embedding for the input text section
        emb = await create_embedding(client=openai_client, engine=args.openaideployment, input=section)
        if emb is not None:
            # Return a dictionary with the processed section details, like id, content, embedding, etc.
            if category is None or role_config is None:
                roles = ["public"]
            else:
                roles = role_config.get(category, ["public"])

            yield {
                "id": id,
                "content": section,
                "embedding": emb.data[0].embedding,
                "doclang": detectLang(text=section, detector=detector),
                "category": category,
                "roles": roles,
                "sourcepage": source,
                "sourcefile": base,
            }
        else:
            raise ValueError("No embedding was created")

        indexed_sources.append(source)

    # call recursive cleanup function with filled counter_dict
    cleanup_lc_sections_from_index(
        counter_dict=counter_dict,
        index_name=args.index,
        search_creds=search_creds,
        search_service=args.searchservice,
    )

    cleanup_lc_corpses_from_index(
        file_name=base,
        indexed_sources=indexed_sources,
        index_name=args.index,
        search_creds=search_creds,
        search_service=args.searchservice,
    )


# SCRIPT EXECUTION BEGINS
args = parser.parse_args()


async def main():

    azure_credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    # OpenAI setup
    token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")

    openai_client = AsyncAzureOpenAI(
        api_version="2023-07-01-preview",
        azure_endpoint=f"https://{args.openaiservice}.openai.azure.com",
        azure_ad_token_provider=token_provider,
    )

    def get_credentials(
        searchkey=args.searchkey,
        storagekey=args.storagekey,
        tenantid=args.tenantid,
        localpdfparser=args.localpdfparser,
        formrecognizerservice=args.formrecognizerservice,
        formrecognizerkey=args.formrecognizerkey,
    ):
        # Use the current user identity to connect to Azure services unless a key is explicitly set for any of them
        azd_credential = (
            AzureDeveloperCliCredential()
            if tenantid is None
            else AzureDeveloperCliCredential(tenant_id=tenantid, process_timeout=60)
        )
        default_creds = azd_credential if searchkey is None or storagekey is None else None
        search_creds = default_creds if searchkey is None else AzureKeyCredential(searchkey)
        storage_creds = default_creds if storagekey is None else storagekey
        if not localpdfparser:
            # check if Azure Form Recognizer credentials are provided
            if formrecognizerservice is None:
                print(
                    "Error: Azure Form Recognizer service is not provided. Please provide formrecognizerservice  \
                        or use --localpdfparser for local pypdf parser."
                )
                exit(1)
            formrecognizer_creds = default_creds if formrecognizerkey is None else AzureKeyCredential(formrecognizerkey)

        return (
            search_creds,
            storage_creds,
            default_creds,
            azd_credential,
            formrecognizer_creds,
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
    ) = get_credentials()

    # INDEX HANDLING BEGINS
    if args.reset_index == "true":
        delete_search_index(
            index_name=args.index,
            search_creds=search_creds,
            searchservice=args.searchservice,
        )
        remove_all_blobs_from_container(
            container_name=args.containerdocs,
            storage_account=args.storageaccount,
            storage_creds=storage_creds,
            verbose=args.verbose,
        )
    # create index (or not if it already exists)
    create_search_index(
        index_name=args.index,
        search_creds=search_creds,
        searchservice=args.searchservice,
        verbose=args.verbose,
    )

    print("data")
    print(args.data_mode)
    print(args.lc_mode)

    if args.data_mode == "lc" or args.data_mode == "all":
        # handling of LANGCHAIN connector

        # TODO: show current loaded langchain documents in pipeline

        if args.lc_mode == "delete":
            print("---> langchain data deletion")
            try:
                f = open("langchain_config.json")
                config = json.load(f)
                for item in config:
                    try:
                        delete_base = item["config"]["url"]
                        if item["loader"] == "confluence":
                            delete_base += f'/display/{item["config"]["space_key"]}'
                        remove_lc_from_index(
                            base=delete_base,
                            index_name=args.index,
                            search_creds=search_creds,
                            searchservice=args.searchservice,
                        )
                    except Exception as e:
                        print(e)
                        print(f'removing data from index {args.index} with base {item["config"]["url"]}')

            except Exception as e:
                print(e)
                print(f"removing data from index {args.index} failed")

        elif args.lc_mode == "create":
            print("---> langchain data indexing")
            try:
                f = open("langchain_config.json")
                config = json.load(f)
                for item in config:
                    if check_time(start_time):
                        print("Refreshing credentials")
                        (
                            search_creds,
                            storage_creds,
                            default_creds,
                            azd_credential,
                            formrecognizer_creds,
                        ) = get_credentials()
                        start_time = time.time()
                    document_map = handle_lc_config_item(item)
                    if document_map == -1:
                        continue
                    splitter = item.get("splitter")
                    splitter = "standard" if splitter not in ["standard", "recursive"] else splitter
                    print("creating sections ...")
                    lc_sections = create_langchain_sections(
                        openai_client,
                        document_map=document_map,
                        search_creds=search_creds,
                        splitter=splitter,
                        category=item.get("category"),
                    )
                    print("indexing sections...")
                    await index_sections(
                        index_name=args.index,
                        searchservice=args.searchservice,
                        search_creds=search_creds,
                        file={item["loader"]},
                        sections=lc_sections,
                    )
                    print(f'{item["loader"]} was processed and indexed sucessfully')

                print("---> langchain data successfully indexed")

            except Exception as e:
                print("config could not be loaded or processed properly")
                print(e)

    else:
        print("---> no langchain data deletion or indexing was requested")

    #  handling of the files
    if args.data_mode == "file" or args.data_mode == "all":
        # data conversion and deleting

        # delete non pdf files from data
        delete_non_pdf_files(args.files)

        # FILE CONVERTION BEGINS

        if args.data_conversion == "true":
            convert_files(folder=args.files2convert)

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

        print("---> file indexing")

        if args.file_mode == "git":
            print("---> file mode is git, local/git files will be used as source for indexing")

            for root, dirs, files in os.walk(args.files):
                for file in files:
                    file_path = os.path.join(root, file)
                    sp_path = file_path.split("/")
                    category = sp_path[1] if (sp_path[1] != file) else None

                    local_hashmap[name_from_path(file_path=file_path, files_directory=args.files)] = [
                        file_path,
                        get_md5_hash(file_path),
                        category,
                    ]
                    if invalidFileName(file):
                        raise Exception(f"The filename {file} is invalid, as it is not allowed to end with -012.pdf etc.")

            # creation of the blob hashmap with the blob.name (file_name) and the md5hash as value
            for blob in blob_list:
                if blob.content_settings.content_md5 is not None:
                    blob_hashmap[blob.name] = bytes(blob.content_settings.content_md5)
                else:
                    blob_hashmap[blob.name] = bytes()
                    print(f"no hash for blob found for {blob.name}")

            # loop through local files
            print("checking local files...")

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
                    ) = get_credentials()
                    start_time = time.time()

                # get category and file_path
                local_category = local_data[2]
                file_path_local = local_data[0]

                # check if the file is in the blob
                if file in blob_hashmap:
                    # if true, get the hash and category for comparison
                    remote_hash = blob_hashmap[file]

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
                                openai_client,
                                file_path_local,
                                page_map,
                                local_category,
                            )

                            await index_sections(
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
                            remove_file_from_index(
                                file_path=file_path_local,
                                index_name=args.index,
                                search_creds=search_creds,
                                searchservice=args.searchservice,
                                file_directory=args.files,
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
                            openai_client,
                            file_path_local,
                            page_map,
                            local_category,
                        )

                        await index_sections(
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
                        remove_file_from_index(
                            file_path=file_path_local,
                            index_name=args.index,
                            search_creds=search_creds,
                            searchservice=args.searchservice,
                            file_directory=args.files,
                        )
                        break

            # loop through blob files
            print("checking remote files...")
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
                        remove_file_from_index(
                            file_path=file,
                            isPath=False,
                            index_name=args.index,
                            search_creds=search_creds,
                            searchservice=args.searchservice,
                            file_directory=args.files,
                        )
                        overview[2] += 1
                    except Exception as e:
                        print("something went wrong with the deletion of files, please contact the Azure Team")
                        print("Error:", e)
                        break
        # -------- FILE MODE BLOB -------- #
        elif args.file_mode == "blob":
            print("---> file mode is blob, blob will be used as source for indexing")
            container_data = docs_service.get_container_client(args.containerdata)

            blobs = list(container_data.list_blobs())

            indexed_blobs = list(docs_container.list_blobs())

            # check regarding deletion of files
            print("---> checking remote indexed files...")
            for blob in indexed_blobs:
                blob_name = blob.name
                try:
                    if check_time(start_time):
                        print("Refreshing credentials")
                        (
                            search_creds,
                            storage_creds,
                            default_creds,
                            azd_credential,
                            formrecognizer_creds,
                        ) = get_credentials()
                        start_time = time.time()

                    if (blob_name not in [data_blob.name for data_blob in blobs]) and (
                        blob_name not in [data_blob.name.replace("_", "/", 1) for data_blob in blobs]
                    ):
                        print(f"-----> {blob_name} only indexed and not in data, will be removed from blob and index")
                        remove_blobs_docs(
                            file_path=blob_name,
                            files_directory=args.containerdata,
                            containerdocs=args.containerdocs,
                            storageaccount=args.storageaccount,
                            storage_creds=storage_creds,
                            verbose=args.verbose,
                            isPath=False,
                        )
                        remove_file_from_index(
                            file_path=blob_name,
                            isPath=False,
                            index_name=args.index,
                            search_creds=search_creds,
                            searchservice=args.searchservice,
                            file_directory=args.containerdata,
                        )
                        overview[2] += 1
                except Exception as e:
                    print("!!! something went wrong with the deletion of files, please contact the Azure Team")
                    print("Error:", e)
                    break

            # check regarding updating/adding files
            print("---> checking data blob files...")
            for blob in blobs:
                if invalidFileName(blob.name):
                    raise Exception(f"!!! The filename {blob.name} is invalid, as it is not allowed to end with -012.pdf etc.")
                if not blob.name.endswith(".pdf"):
                    print(f"-----> {blob.name} is not a pdf file, will be skipped")
                    continue
                blob_name = blob.name
                try:
                    if check_time(start_time):
                        print("Refreshing credentials")
                        (
                            search_creds,
                            storage_creds,
                            default_creds,
                            azd_credential,
                            formrecognizer_creds,
                        ) = get_credentials()
                        start_time = time.time()
                    blob_url = f"https://{args.storageaccount}.blob.core.windows.net/{args.containerdata}/{quote(blob_name)}"

                    # Check if the blob is in a level 2 subfolder or deeper
                    if blob_name.count("/") > 1:
                        print(f"!! Copying blob '{blob_name}' is not allowed because it is in a level 2 subfolder or deeper.")
                        continue

                    if "_" in blob_name.split("/")[0] and blob_name.count("/") > 0:
                        print(f"!! Underscore in folder '{blob_name}' is not allowed because it is in a level 1 subfolder.")
                        continue

                    local_category = blob_name.split("/")[0] if blob_name.count("/") > 0 else None

                    # Modify the blob name to include the subfolder name
                    new_blob_name = blob_name.replace("/", "_")
                    copied_blob = docs_container.get_blob_client(new_blob_name)
                    existed = True
                    if copied_blob.exists():
                        existing_blob_data = docs_container.download_blob(new_blob_name)
                        existing_blob_md5 = (
                            existing_blob_data.properties.content_settings.content_md5 if existing_blob_data.properties else None
                        )

                        source_blob_data = container_data.download_blob(blob_name)
                        source_blob_md5 = (
                            source_blob_data.properties.content_settings.content_md5 if source_blob_data.properties else None
                        )

                        if source_blob_md5 == existing_blob_md5:
                            print(f"-----> {new_blob_name} is similar to indexed one, indexing will be skipped")
                            continue
                        else:
                            print(f"-----> {new_blob_name} is not similar to indexed one")
                    else:
                        existed = False

                    copied_blob.start_copy_from_url(blob_url)
                    page_map = get_document_text_from_blob(
                        blob_client=copied_blob,
                        formrecognizer_creds=formrecognizer_creds,
                        formrecognizerservice=args.formrecognizerservice,
                    )
                    sections = create_document_blob_sections(openai_client, new_blob_name, page_map, local_category)
                    await index_sections(
                        index_name=args.index,
                        searchservice=args.searchservice,
                        search_creds=search_creds,
                        file=blob_url,
                        sections=sections,
                    )
                    print("-----> sections indexed")
                    if existed:
                        overview[0] += 1
                    else:
                        overview[1] += 1
                    copied_blob.close()
                except Exception as e:
                    print("!!! something went wrong during indexing, clearing up state now")
                    print(e)
                    remove_blobs_docs(
                        file_path=blob_name,
                        files_directory=args.files,
                        containerdocs=args.containerdocs,
                        storageaccount=args.storageaccount,
                        storage_creds=storage_creds,
                        isPath=False,
                        verbose=args.verbose,
                    )
                    remove_file_from_index(
                        file_path=blob_name,
                        index_name=args.index,
                        isPath=False,
                        search_creds=search_creds,
                        searchservice=args.searchservice,
                        file_directory=args.files,
                    )
                    break
        print(
            f"---> file indexing sucessfully {str(overview[0])} files were changed, {str(overview[1])} \
files were added, {str(overview[2])} files were deleted"
        )
    else:
        print("---> no file data deletion, updating or indexing was requested")

    if role_config:
        update_roles_index(
            index_name=args.index,
            searchservice=args.searchservice,
            searchcreds=search_creds,
            role_config=role_config,
        )

    await openai_client.close()
    await azure_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
