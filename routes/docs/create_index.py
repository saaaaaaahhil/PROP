from langchain_openai import OpenAIEmbeddings
from azure.search.documents.indexes.models import (
    CorsOptions,
    ScoringProfile,
    VectorSearch,
    HnswAlgorithmConfiguration,
    HnswParameters,
    VectorSearchAlgorithmKind,
    VectorSearchAlgorithmMetric,
    ExhaustiveKnnAlgorithmConfiguration,
    ExhaustiveKnnParameters,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    VectorSearchProfile,
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField
)
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

from typing import List

from config import Config
from routes.docs.embeddings import get_embeddings

def create_or_update_index(project_id: str):
    """
    This function creates or updates the index for a given project.
    """
    try:
        service_endpoint = Config.AZURE_SEARCH_SERVICE_ENDPOINT
        index_name = project_id
        key = Config.AZURE_SEARCH_API_KEY

        embeddings = get_embeddings()

        cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=300)
        scoring_profiles: List[ScoringProfile] = []
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default",
                    kind=VectorSearchAlgorithmKind.HNSW,
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric=VectorSearchAlgorithmMetric.COSINE,
                    ),
                ),
                ExhaustiveKnnAlgorithmConfiguration(
                    name="default_exhaustive_knn",
                    kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                    parameters=ExhaustiveKnnParameters(
                        metric=VectorSearchAlgorithmMetric.COSINE
                    ),
                ),
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="default",
                ),
                VectorSearchProfile(
                    name="myExhaustiveKnnProfile",
                    algorithm_configuration_name="default_exhaustive_knn",
                ),
            ],
        )

        semantic_configuration = SemanticConfiguration(
            name=Config.AZURE_SEARCH_SEMANTIC_CONFIGURATION_NAME,
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
            ),
        )
        semantic_search = SemanticSearch(configurations=[semantic_configuration])

        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=len(embeddings.embed_query("Text")),
                vector_search_profile_name="myHnswProfile",
            ),
            SimpleField(
                name="project_id",
                type=SearchFieldDataType.String
            ),
            SimpleField(
                name="source",
                type=SearchFieldDataType.String
            ),
        ]

        index = SearchIndex(name=index_name, fields=fields, scoring_profiles=scoring_profiles, cors_options=cors_options, vector_search=vector_search, semantic_search=semantic_search)
        client = SearchIndexClient(service_endpoint, AzureKeyCredential(key))
        result = client.create_or_update_index(index)
        print(f"Index created or updated: {result}")
        return {"success" : True, "message" : f"Index created or updated: {result}"}
    except Exception as e:
        print(f"Error creating or updating index: {e}")
        raise
        return {"success" : False, "message" : f"Error creating or updating index: {e}"}