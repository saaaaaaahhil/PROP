from fastapi import APIRouter
from fastapi import Form
from fastapi.responses import JSONResponse
import time
from starlette.concurrency import run_in_threadpool
from concurrent.futures import ThreadPoolExecutor, as_completed

from routes.query_router.preprocess_query import preprocess_query, aggregate_queries

from routes.csv.sql_agent import run_query
from routes.metadata.run_md_query import run_md_query
from routes.docs.search import run_rag_pipeline
from routes.images.image_agent import query_images

router = APIRouter(prefix='/run_user_query', tags=['final_query'])

@router.post('/query')
async def run_user_query(
    project_id: str = Form(...),
    query: str = Form(...)):
    start_time = time.time()
    try:
        #Get categories of queries through classifier
        response = await run_in_threadpool(preprocess_query, query)

        # Mapping of functions and category
        category_functions = {
            'csv': run_query,
            'metadata': run_md_query,
            'docs': run_rag_pipeline,
            'vision': query_images,
            'general' : run_rag_pipeline,
            'other': other_query
        }

        if len(response) == 1:
            #Single query execution
            ans = await run_in_threadpool(execute_single_query, response[0], category_functions, project_id)
            if ans['success']:
                return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', 'response_time': f'{round(time.time()-start_time,2)}s', 'result': ans['answer']})
            else:
                return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database', 'response_time': f'{round(time.time()-start_time,2)}s'})
        else:
            #Multiple queries are executed parallely.
            aggregated_queries = aggregate_queries(response)
            ans = await run_in_threadpool(execute_queries_parallel, category_functions, project_id, aggregated_queries)
            return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', 'response_time': f'{round(time.time()-start_time,2)}s', 'result': ans})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}', 'response_time': f'{round(time.time()-start_time,2)}s'})
    
def other_query(project_id: str, query: str):
    return {'success': True, 'answer': 'The query is out of scope for this project.'}

def execute_single_query(response: dict, category_functions: dict, project_id: str):
    try:
        category = response['category']
        if category not in category_functions:
            raise
        query = response['query']
        ans = category_functions[category](project_id, query)
        if ans['success']:
            return {'success': True, 'answer': ans['answer']}
        else:
            return {'success': False}
    except Exception as e:
        return {'success': False}
    
def execute_queries_parallel(category_functions: dict, project_id: str, response: list):
    final_response = []

    with ThreadPoolExecutor() as executor:
        # Submit tasks to the executor
        futures = []
        for result in response:
            if result['category'] in category_functions:
                if result['category'] == 'general':
                    futures.append(executor.submit(category_functions[result['category']], 'general', result['query']))
                else:
                    futures.append(executor.submit(category_functions[result['category']], project_id, result['query']))

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                ans = future.result()
                if ans['success']:
                    final_response.append(ans.get('answer', ''))
                else:
                    raise Exception('Error running query')
            except Exception as e:
                raise Exception(f'Error processing query: {e}')

    return final_response