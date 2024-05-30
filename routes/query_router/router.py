from fastapi import APIRouter
from fastapi import Form
from fastapi.responses import JSONResponse
import time
from starlette.concurrency import run_in_threadpool
from concurrent.futures import ThreadPoolExecutor, as_completed
from routes.query_router.preprocess_query import preprocess_query, aggregate_queries
from routes.mongo_db_functions import get_project_version
from routes.csv.sql_agent import run_query
from routes.metadata.run_md_query import run_md_query
from routes.docs.search import run_rag_pipeline
from routes.images.image_agent import query_images
# from connections.redis import llmcache
import os
from routes.llm_connections import groq_client


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
            return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', 'response_time': f'{round(time.time()-start_time,2)}s', 'result': "\n".join(ans)})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}', 'response_time': f'{round(time.time()-start_time,2)}s'})
    
def other_query(project_id: str, query: str):
    return {'success': True, 'answer': 'The query is out of scope for this project.'}

def execute_single_query(response: dict, category_functions: dict, project_id: str):
    try:
        category = response['category']

        # Check if query category is valid
        if category not in category_functions:
            raise Exception("Query category is invalid.")
        query = response['query']

        #Check for response inside cache
        # print('Checking cache.....')
        # result = check_cache(query, project_id, category)
        # if result: 
            # return {'success': True, 'answer': result[0].get('response','')}
            
        # Give query to LLM
        # print("No entry found in cache")
        ans = category_functions[category](project_id, query)

        if ans['success']:
            #Store response inside cache
            # add_to_cache(query, project_id, ans['answer'], {'project_id': project_id, "category": category})
            return {'success': True, 'answer': ans['answer']}
        else:
            return {'success': False}
    except Exception as e:
        print(f'Failed to execute query: {e}')
        return {'success': False}
    
def execute_queries_parallel(category_functions: dict, project_id: str, response: list):
    final_response = []

    with ThreadPoolExecutor() as executor:
        # Submit tasks to the executor
        futures = []
        for result in response:
            query = result['query']
            category = result['category']
            if category in category_functions:
                # Check cache for response
                # if check := check_cache(query, project_id, category):
                    # final_response.append(check[0].get('response', ''))
                # else:
                if category == 'general':
                    future = executor.submit(category_functions[category], 'general', query)
                else:
                    future = executor.submit(category_functions[category], project_id, query)
                    
                futures.append((future, query, category))

        # Collect results as they complete
        for future, query, category in futures:
            try:
                ans = future.result()
                if ans['success']:
                    # add_to_cache(query, project_id, ans['answer'], {'project_id': project_id, 'category': category})
                    final_response.append(ans.get('answer', ''))
            except Exception as e:
                raise Exception(f'Error processing query: {e}')

    return final_response

# def check_cache(query: str, project_id: str, category: str):
#     try:

#         result = llmcache.check(prompt= query, return_fields=["response", 'metadata'])
#         if len(result) == 0:
#             return None
        
#         cache_project_id = result[0].get('metadata').get('project_id')
#         cache_project_version = result[0].get('metadata').get('version')
#         cache_query_category =  result[0].get('metadata').get('category')

#         current_version = get_project_version(project_id)

#         if cache_project_version == current_version and project_id == cache_project_id and category == cache_query_category:
#             print("Cache Hit.")
#             print(result)
#             return result
        
#         return None
    
#     except Exception as e:
#         print(f"Error checking cache: {e}")
#         return None
    

# def add_to_cache(query: str, project_id: str, response: str, meta_data: dict):
#     try:
#         print("Storing inside cache")
#         version_no = get_project_version(project_id)
#         meta_data['version'] = version_no
#         llmcache.store(
#             prompt=query,
#             response=response,
#             metadata = meta_data
#         )
#     except Exception as e:
#         print(f"Error storing into cache: {e}")

# def summarize_response(final_responses: list, query: str):
#     try:
#         messages=[
#             {
#                 "role": "system",
#                 "content": """You are a Natural Language Processing API capable of summarizing the text and respond in JSON. The JSON schema should include:
#                 {
#                     'summary' : 'summary of user query'
#                 }
#                 You will be given the list of responses along with the user query. Summarize the responses without losing any information. If there is no response/result for a query then skip that response. List of responses: """
#             },
#             {
#                 "role": "user",
#                 "content": f'List of responses: {str(final_responses)}, user query: {query}'
#             }
#         ]
#         response = client.chat.completions.create(
#             model=MODEL,
#             messages=messages,
#             temperature=0.5,
#             max_tokens=,
#             top_p=1,
#             stream=False,
#             response_format={"type": "json_object"},
#             stop=None
#         )
#         response_message = response.choices[0].message.content
#         json_string = response_message
#         json_object = json.loads(json_string)
#         return json_object["category"]

#     except Exception as e:
#         print(f"Error predicting category: {e}")
#         raise RetryableException(f"Error predicting category: {e}")