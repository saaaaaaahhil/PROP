from azure.search.documents.models import VectorizedQuery
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import numpy as np
import os
from routes.llm_connections import llm_openai
from config import Config
from routes.docs.embeddings import get_embeddings
from routes.docs.index_search_client import get_index_client

llm = llm_openai
llm.temperature = 0

def get_top_k_results(project_id, query):
    """
    This function takes a query and returns the top k results from the rag pipeline.
    """
    try:
        embeddings = get_embeddings()

        # Get the search client
        search_client = get_index_client(project_id)
        if not search_client:
            raise Exception("Error retrieving search index client.")
            return {"success": False, "message": "Error retrieving search index client."}
        
        results = search_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=np.array(embeddings.embed_query(query), dtype=np.float32).tolist(),
                    k_nearest_neighbors=Config.TOP_K,
                    fields="content_vector",
                )
            ],
            semantic_configuration_name=Config.AZURE_SEARCH_SEMANTIC_CONFIGURATION_NAME,
            query_type="semantic",
            query_caption="extractive",
            query_answer="extractive",
            top=Config.TOP_K)

        top_k_results_content = []
        for result in results:
            top_k_results_content.append(result["content"])

        return {"success": True, "results": top_k_results_content}

    except Exception as e:
        print(f"Error getting top k results: {e}")
        raise
        return {"success": False, "message": str(e)}

def generate_response(results, query):
    """
    This function generates a response from the RAG pipeline results.
    """
    context = ""
    for result in results:
        context += f"{result}\n"

    prompt = ChatPromptTemplate.from_messages([("system", Config.RAG_SYSTEM_PROMPT), ("human", query)])
    chain = prompt | llm
    response = chain.invoke({"context": context})
    return response.content

def run_rag_pipeline(project_id, query):
    """
    This function takes a query and runs the RAG pipeline to generate an answer.
    """
    try:
        # Get the top k results
        top_k_results = get_top_k_results(project_id, query)
        if not top_k_results["success"]:
            return {"success": False, "message": top_k_results["message"]}

        # Run the RAG pipeline
        response = generate_response(top_k_results["results"], query)

        return {"success": True, "answer": response}

    except Exception as e:
        print(f"Error running RAG pipeline: {e}")
        return {"success": False, "failure": f'Error in docs agent: {e}'}
