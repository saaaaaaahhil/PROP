from fastapi import APIRouter
from fastapi import Form
from fastapi.responses import JSONResponse

from starlette.concurrency import run_in_threadpool

from routes.metadata.run_md_query import run_md_query

router = APIRouter(prefix='/metadata', tags=['metadata'])

@router.post('/query_metadata')
async def run_metadata_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        response = await run_in_threadpool(run_md_query, project_id , query)

        if response['success']:
            return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', "result": response['answer']})
        else:
            return JSONResponse(status_code=500, content={"message": f'Error getting response on query {query} for project {project_id}.'})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}'})






