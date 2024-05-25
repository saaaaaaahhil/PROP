from routes.pitch.pitch_agent import generate_queries_from_pitch, get_query_category, summarize_to_generate_pitch
from routes.query_router.router import execute_queries_parallel
from starlette.concurrency import run_in_threadpool

from routes.csv.sql_agent import run_query
from routes.metadata.run_md_query import run_md_query
from routes.docs.search import run_rag_pipeline
from routes.images.image_agent import query_images
from routes.query_router.preprocess_query import aggregate_queries

def other_query(project_id: str, query: str):
    return {'success': True, 'answer': 'The query is out of scope for this project.'}

async def generate_pitch(project_id: str, query:str):
    """
    This function return the generated pitch
    """
    try:
        print("Processing pitch query")

        #Get list of queries from user input
        query_list = await run_in_threadpool(generate_queries_from_pitch, query)
        print(query_list)

        #Aggregate docs and vision queries
        aggregated_query_list = aggregate_queries(query_list)

        # Mapping of functions and category
        category_functions = {
            'csv': run_query,
            'metadata': run_md_query,
            'docs': run_rag_pipeline,
            'vision': query_images,
            'general' : run_rag_pipeline,
            'other': other_query
        }

        # Process each query separately and generate a response
        response = await run_in_threadpool(execute_queries_parallel, category_functions, project_id, aggregated_query_list)
        data = ','.join([str(i) for i in response])

        #Use proccessed query to generate a pitch
        pitch = await run_in_threadpool(summarize_to_generate_pitch, query, data)
        print(pitch)
        return {'success': True, "answer": pitch['pitch']}
    except Exception as e:
        raise e