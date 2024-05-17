import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import routes.csv.csv_router as csv_router
import routes.docs.docs_router as docs_router
import routes.images.images_router as images_router
import routes.metadata.metadata_router as metadata_router
from connections.mongo_db import mongodb_client
import routes.query_router.router as query_router
import redis
from config import Config



r = redis.Redis(host='localhost', port=6379, decode_responses=True)


app = FastAPI()

app.include_router(csv_router.router)
app.include_router(docs_router.router)
app.include_router(images_router.router)
app.include_router(metadata_router.router)
app.include_router(query_router.router)

@app.get('/')
async def root():
    return {"message": "Hello World"}

@app.post('/get_files_data')
async def get_files_data(
project_id: str = Form(...)):

    try:
        response = await run_in_threadpool(get_project_files, project_id)

        if response['success']:
            return JSONResponse(status_code=200, content={"message": f'Files retrieved successfully from {project_id} database.', "result": response['answer']})

        else:
            return JSONResponse(status_code=500, content={"message": f'Error retrieving data for project {project_id}.'})

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error retrieving data from {project_id} database: {e}'})


def get_project_files(project_id: str):
    """
        This function return all the files stored for current project
    """

    try:
        db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        response = []
        selection = {'project_id': project_id}
        projection = {'_id': 1, 'file_name': 1, 'file_type' : 1}
        data = collection.find(selection, projection)

        for doc in data:
            response.append(doc)
        
        return {'success': True, 'answer' : response}
    
    except Exception as e:
        print(f"Failed to retrieve the data: {e}")
        raise


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)