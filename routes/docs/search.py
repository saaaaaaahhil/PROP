from azure.search.documents.models import VectorizedQuery
from langchain_openai import ChatOpenAI, AzureChatOpenAI
# from langchain_groq import ChatGroq  # Commented out as it might use Portkey
# from langchain_anthropic import ChatAnthropic  # Commented out as it might use Portkey
from langchain_core.prompts import ChatPromptTemplate
# from portkey_ai import createHeaders, PORTKEY_GATEWAY_URL  # Commented out as it's not to be used
import numpy as np
import os
from config import Config
from routes.docs.embeddings import get_embeddings
from routes.docs.index_search_client import get_index_client
# import anthropic  # Commented out as it's not to be used

system_prompt = """You are a real estate agent. Given the context (which is your knowledge) and the user query, provide the answer in as much detail as possible. While answering the queries:
1. Do not assume any information and strictly adhere to the context provided.
2. Pay special attention to all details, including any exclusions or specific conditions mentioned. It is crucial to include every relevant detail from the context in your answer.
The answer is being given to the end customer and any missing information can lead to huge loss for your firm.
Context: {context}"""

def get_top_k_results(project_id, query):
    """
    This function takes a query and returns the top k results from the RAG pipeline.
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

def generate_response(results, query, project_id, user_id):
    """
    This function generates a response from the RAG pipeline results.
    """
    llm = ChatOpenAI(
            api_key=os.environ['OPENAI_API_KEY'],
            temperature=0.3, 
            model="gpt-4o",  # Changed model to "gpt-4" as "gpt-4o" may not be valid without Portkey
            max_tokens=4096
    )

    context = "\n".join(results)

    print(context)
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", query)])
    chain = prompt | llm
    response = chain.invoke({"context": context})
    return response.content

def run_rag_pipeline(project_id, query, user_id = None):
    """
    This function takes a query and runs the RAG pipeline to generate an answer.
    """
    try:
        # Get the top k results
        top_k_results = get_top_k_results(project_id, query)
        if not top_k_results["success"]:
            return {"success": False, "message": top_k_results["message"]}

        # Run the RAG pipeline
        response = generate_response(top_k_results["results"], query, project_id, user_id)

        return {"success": True, "answer": response}

    except Exception as e:
        print(f"Error running RAG pipeline: {e}")
        return {"success": False, "failure": f'Error in docs agent: {e}'}
