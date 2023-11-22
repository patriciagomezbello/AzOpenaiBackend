from azure.search.documents.indexes.models import (
    HnswParameters,
    SemanticPrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from .helper import name_from_path
import re
import openai
import time


def create_search_index(index_name, search_creds, searchservice, verbose=False):
    if verbose:
        print(f"Ensuring search index {index_name} exists")
    index_client = SearchIndexClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        credential=search_creds,
    )
    if index_name not in index_client.list_index_names():
        index = create_index(index_name)
        if verbose:
            print(f"Creating {index_name} search index")
        index_client.create_index(index)
    else:
        if verbose:
            print(f"Search index {index_name} already exists")


def create_index(indexName):
    return SearchIndex(
        name=indexName,
        fields=[
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(
                name="content", type="Edm.String", analyzer_name="en.microsoft"
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                hidden=False,
                searchable=True,
                filterable=False,
                sortable=False,
                facetable=False,
                vector_search_dimensions=1536,
                vector_search_profile_name="default_vector",
            ),
            SimpleField(
                name="doclang", type="Edm.String", filterable=True, facetable=True
            ),
            SimpleField(
                name="category", type="Edm.String", filterable=True, facetable=True
            ),
            SimpleField(
                name="accesskeys",
                type="Collection(Edm.String)",
                filterable=True,
                retrievable=False,
                Nullable=True,
            ),
            SimpleField(
                name="sourcepage",
                type="Edm.String",
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="sourcefile",
                type="Edm.String",
                filterable=True,
                facetable=True,
            ),
        ],
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=None,
                        content_fields=[SemanticField(field_name="content")],
                    ),
                )
            ]
        ),
        vector_search=VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default_vector",
                    algorithm_configuration_name="default_hnsw_config",
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default_hnsw_config",
                    hnsw_parameters=HnswParameters(metric="cosine"),
                )
            ],
        ),
    )


def index_sections(
    index_name, searchservice, search_creds, file, sections, verbose=False
):
    if verbose:
        print(f"Indexing sections from '{file}' into search index '{index_name}'")
    search_client = SearchClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if verbose:
                print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        if verbose:
            print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")


def remove_from_index(
    file_path,
    index_name,
    search_creds,
    searchservice,
    file_directory,
    isPath=True,
    verbose=False,
):
    if verbose:
        print(
            f"Removing sections from '{file_path or '<all>'}' from search index '{index_name}'"
        )
    search_client = SearchClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )
    file = name_from_path(file_path, file_directory) if isPath else file_path
    while True:
        filter = None if file_path is None else f"sourcefile eq '{file}'"
        r = search_client.search("", filter=filter, top=1000, include_total_count=True)
        if r.get_count() == 0:
            break
        r = search_client.delete_documents(documents=[{"id": d["id"]} for d in r])
        if verbose:
            print(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)


# updates only the category of a file (returns nothing)
def update_search_value(index_name, search_creds, searchservice, file, key, value):
    search_client = SearchClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )
    results = search_client.search(search_text="*", filter=f"sourcefile eq '{file}'")
    updated_docs = []
    for res in results:
        res[key] = value
        updated_docs.append(res)

    search_client.upload_documents(documents=updated_docs)


def create_embedding(engine, input):
    try:
        emb = openai.Embedding.create(engine=engine, input=input)
    except openai.error.RateLimitError as e:
        print(e)
        # Extract any number from the error message
        number = re.search(r"\d+", str(e))
        # Convert the number to integer, if not found, default to 10 seconds
        secondsToWait = int(number.group()) if number else 10
        # Print the wait time
        print(f"Waiting now for {secondsToWait} seconds")
        # Wait for the specified time before trying again
        time.sleep(secondsToWait)
        # Retry creating the OpenAI Embedding for the input section
        emb = create_embedding(engine=engine, input=input)
    except openai.error.APIConnectionError as e:
        print(e)
        print("Waiting now for 5 seconds")
        time.sleep(5)
        # Retry creating the OpenAI Embedding for the input section
        emb = create_embedding(engine=engine, input=input)
    except openai.error.ServiceUnavailableError as e:
        print(e)
        print("Waiting now for 60 seconds")
        time.sleep(60)
        # Retry creating the OpenAI Embedding for the input section
        emb = create_embedding(engine=engine, input=input)
    return emb
