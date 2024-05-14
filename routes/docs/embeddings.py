from langchain_openai import OpenAIEmbeddings, AzureOpenAIEmbeddings
import os

from config import Config

def get_embeddings():
    # embeddings = OpenAIEmbeddings(model=Config.OPENAI_EMBEDDING_MODEL)
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ['AZURE_OPENAI_EMBEDDING_NAME'],
        openai_api_version=os.environ['AZURE_OPENAI_API_VERSION'],
    )
    return embeddings