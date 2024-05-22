from fastapi import APIRouter
from fastapi import Form
from fastapi.responses import JSONResponse

from starlette.concurrency import run_in_threadpool

from routes.query_router.preprocess_query import preprocess_query

from routes.csv.sql_agent import run_query
from routes.metadata.run_md_query import run_md_query
from routes.docs.search import run_rag_pipeline
from routes.images.image_agent import query_images

router = APIRouter(prefix='/run_user_query', tags=['final_query'])

@router.post('/query')
async def run_user_query(
    project_id: str = Form(...),
    query: str = Form(...)):
    try:
        final_response = []
        response = await run_in_threadpool(preprocess_query, query)

        category_functions = {
            'csv': run_query,
            'metadata': run_md_query,
            'other': run_rag_pipeline,
            'vision': query_images,
            'general' : run_rag_pipeline
        }

        for result in response:
            category = result['category']
            if category in category_functions:
                ans = await run_in_threadpool(category_functions[category], project_id, result['query'])
                if ans['success']:
                    final_response.append(ans.get('answer', ''))
                else:
                    return JSONResponse(status_code=500, content={"message": f'Error running query'})
            else:
                return JSONResponse(status_code=500, content={"message": f'Unknown category: {category}'})
        
        return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', 'result': final_response})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}'})