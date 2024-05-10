from langchain_openai import OpenAIEmbeddings
import os

from config import Config

def get_embeddings():
    embeddings = OpenAIEmbeddings(model=Config.OPENAI_EMBEDDING_MODEL)
    return embeddings