from __future__ import annotations

from azure.search.documents.indexes.models import _edm as FieldType
from azure.search.documents.indexes.models import HnswAlgorithmConfiguration
from azure.search.documents.indexes.models import HnswParameters
from azure.search.documents.indexes.models import SearchableField
from azure.search.documents.indexes.models import SearchField
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.indexes.models import SemanticConfiguration
from azure.search.documents.indexes.models import SemanticField
from azure.search.documents.indexes.models import SemanticPrioritizedFields
from azure.search.documents.indexes.models import SemanticSearch
from azure.search.documents.indexes.models import SimpleField
from azure.search.documents.indexes.models import VectorSearch
from azure.search.documents.indexes.models import VectorSearchAlgorithmConfiguration
from azure.search.documents.indexes.models import VectorSearchProfile


def new_index(name: str) -> SearchIndex:
    return (
        IndexBuilder(name)
        .add_fields(*INDEX_FIELDS)
        .add_semantic_search_config(
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=None, content_fields=[SemanticField(field_name="content")]
                ),
            )
        )
        .add_vector_search_profiles(VectorSearchProfile(name="default_vector", algorithm_configuration_name="default_hnsw_config"))
        .add_vector_search_algorithms(
            HnswAlgorithmConfiguration(
                name="default_hnsw_config",
                parameters=HnswParameters(metric="cosine"),
            )
        )
        .build()
    )


class IndexBuilder:
    def __init__(self, name: str) -> None:
        self.name = name
        self.fields: list[SearchField] = []
        self.semantic_search_config: list[SemanticConfiguration] = []
        self.vector_search_profiles: list[VectorSearchProfile] = []
        self.vector_search_algorithms: list[VectorSearchAlgorithmConfiguration] = []

    def set_name(self, name: str) -> IndexBuilder:
        self.name = name
        return self

    def add_fields(self, *fields: SearchField) -> IndexBuilder:
        self.fields.extend(fields)
        return self

    def add_semantic_search_config(self, *configs: SemanticConfiguration) -> IndexBuilder:
        self.semantic_search_config.extend(configs)
        return self

    def add_vector_search_profiles(self, *profiles: VectorSearchProfile) -> IndexBuilder:
        self.vector_search_profiles.extend(profiles)
        return self

    def add_vector_search_algorithms(self, *algorithms: VectorSearchAlgorithmConfiguration) -> IndexBuilder:
        self.vector_search_algorithms.extend(algorithms)
        return self

    def build(self) -> SearchIndex:
        if self.name == "":
            raise ValueError("Name is required")

        return SearchIndex(
            name=self.name,
            fields=self.fields,
            semantic_search=SemanticSearch(configurations=self.semantic_search_config),
            vector_search=VectorSearch(
                profiles=self.vector_search_profiles,
                algorithms=self.vector_search_algorithms,
            ),
        )


class IndexField:
    Simple = SimpleField
    Searchable = SearchableField
    Custom = SearchField


INDEX_FIELDS: list[SearchField] = [
    IndexField.Simple(name="id", type=FieldType.String, key=True),
    IndexField.Searchable(name="content", type=FieldType.String, analyzer_name="en.microsoft"),
    IndexField.Custom(
        name="embedding",
        type=FieldType.Collection(FieldType.Single),
        hidden=False,
        searchable=True,
        filterable=False,
        sortable=False,
        facetable=False,
        vector_search_dimensions=1536,
        vector_search_profile_name="default_vector",
    ),
    IndexField.Simple(name="doclang", type=FieldType.String, filterable=True, facetable=True),
    IndexField.Simple(name="category", type=FieldType.String, filterable=True, facetable=True),
    IndexField.Simple(
        name="roles",
        type=FieldType.Collection(FieldType.String),
        filterable=True,
        retrievable=False,
        facetable=True,
        Nullable=True,
    ),
    IndexField.Simple(
        name="sourcepage",
        type=FieldType.String,
        filterable=True,
        facetable=True,
    ),
    IndexField.Simple(
        name="sourcefile",
        type=FieldType.String,
        filterable=True,
        facetable=True,
    ),
]
