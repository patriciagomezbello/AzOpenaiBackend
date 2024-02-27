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
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient
from openai import (
    AsyncAzureOpenAI,
    RateLimitError,
    APIConnectionError,
)
from .helper import name_from_path, url_to_id_cleanup
import re
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


def delete_search_index(index_name, search_creds, searchservice, verbose=False):
    print(f"deleting search index {index_name}")
    index_client = SearchIndexClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        credential=search_creds,
    )
    index_client.delete_index(index=index_name)


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


def remove_file_from_index(
    file_path,
    index_name,
    search_creds,
    searchservice,
    file_directory,
    isPath=True,
):
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
        filter = f"sourcefile eq '{file}'"
        r = search_client.search("", filter=filter, top=1000, include_total_count=True)
        if r.get_count() == 0:
            break
        r = search_client.delete_documents(documents=[{"id": d["id"]} for d in r])
        print(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)


def remove_lc_from_index(
    base,
    index_name,
    search_creds,
    searchservice,
):
    print(
        f"Removing sections from '{base or '<all>'}' from search index '{index_name}'"
    )

    search_client = SearchClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )
    while True:
        filter = f"sourcefile eq '{base}'"
        r = search_client.search("", filter=filter, top=1000, include_total_count=True)
        if r.get_count() == 0:
            break
        r = search_client.delete_documents(documents=[{"id": d["id"]} for d in r])
        print(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)


def cleanup_lc_sections_from_index(
    counter_dict: dict[str, int],
    index_name: str,
    search_creds,
    search_service: str,
) -> None:
    """
    Cleanup documents from specified azure search index based on the given counter dictionary.

    Args:
        counter_dict: A dictionary in which keys are url's and values are number of documents with that url.
        index_name: Azure search index name from where documents need to be deleted.
        search_creds: Credential for connecting azure search service.
        search_service: Azure search service name.

    Returns:
        None
    """
    print(f"Starting cleanup of search index '{index_name}'...")

    # Create a search client for the specified azure search service and index
    search_client = SearchClient(
        endpoint=f"https://{search_service}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )

    # Iterating through all the url's in counter dictionary
    for key in counter_dict:
        cleanup_num = counter_dict[key] + 1
        # Performing recursive cleanup operation on each url
        cleanup_search_recursive(search_client=search_client, key=key, num=cleanup_num)
    print(f"Cleanup of search index '{index_name}' finished.")


def cleanup_search_recursive(search_client: SearchClient, key: str, num: int) -> None:
    """
    Recursive function to delete documents from azure search index.

    Args:
        search_client: Azure search client object for interacting with azure search service.
        key: URL of the document.
        num: Number denotes how many documents with that URL needs to be deleted.

    Returns:
        None
    """
    # Transform the url to the id format used in the search index
    id = url_to_id_cleanup(url=key, number=num)

    # Search for documents where id equals the generated document id
    try:
        result = search_client.get_document(
            key=id, selected_fields=["id", "sourcepage"]
        )
        print(result)
        # Delete the documents that were found
        delete_result = search_client.delete_documents(documents=[{"id": id}])
        print(f"\tDeleted {len(delete_result)} documents from index")
        # It can take a few seconds for search results to reflect changes, so wait a bit
        time.sleep(2)
        # Perform the cleanup operation again as there could still be some documents left to be deleted.
        cleanup_search_recursive(search_client, key, num + 1)
    except ResourceNotFoundError:
        print(f"\tNo documents found for deletion with id={id}")
    except Exception as e:
        print(e)
        print(f"unexspected issue while cleaning up lc data with id={id}")


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


def create_embedding(client: AsyncAzureOpenAI, engine, input):
    try:
        emb = client.embeddings.create(model=engine, input=input)
    except RateLimitError as e:
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
        emb = create_embedding(client=client, engine=engine, input=input)
    except APIConnectionError as e:
        print(e)
        print("Waiting now for 60 seconds")
        time.sleep(60)
        # Retry creating the OpenAI Embedding for the input section
        emb = create_embedding(client=client, engine=engine, input=input)
    return emb


async def cgsIndexColumnFacetDist(searchservice, index_name, search_creds, facet):
    search_client = SearchClient(
        endpoint=f"https://{searchservice}.search.windows.net/",
        index_name=index_name,
        credential=search_creds,
    )
    try:
        facets_search = await search_client.search(
            top=0,
            skip=0,
            query_type="simple",
            select="",
            search_text="*",
            search_fields=[],
            filter="",
            facets=[facet],
            order_by="",
            include_total_count=True,
        )
        res = await facets_search.get_facets()
        return res[facet]
    except Exception as e:
        print(e)
        print("setting default to 'de' due to error in facets search query")
        return [{"count": 1, "value": "de"}]
