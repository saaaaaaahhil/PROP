from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

import asyncio
from starlette.concurrency import run_in_threadpool

from fastapi import BackgroundTasks
import uuid

from routes.images.store_operations import upload_image_to_store, delete_image_data
from routes.images.image_agent import query_images
from connections.mongo_db import mongodb_client
from config import Config

router = APIRouter(prefix='/images', tags=['IMAGES'])

async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    project_id: str,
    id: str):

    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        if file.content_type not in ['image/jpeg', 'image/png']:
            return JSONResponse(status_code=400, content={"message": f'File format for {file.filename} not supported, please upload a JPEG or PNG image.'})
        print(f'Uploading file {file.filename} to {project_id} index.')


        file_type = file.content_type
        file_name = file.filename
        contents = await file.read()


        background_tasks.add_task(upload_image_to_store, project_id, contents, file_name, file_type)
        return JSONResponse(status_code=200, content={"message": f'File uploaded successfully.'})
    except Exception as e:
        print(f"Error uploading file: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'_id': id}
        update = {"$set": {"status": "fail"}}
        collection.update_one(query,update,upsert=True)
        return JSONResponse(status_code=500, content={"message": f'Error uploading file.'})
    
@router.post('/run_image_query')
async def run_image_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        print(f'Running query for project {project_id}...')

        response = await run_in_threadpool(query_images, project_id, query)
        if response["success"]:
            return JSONResponse(status_code=200, content={"message": f'Query ran successfully.', "result": response["answer"]})
        else:
            return JSONResponse(status_code=500, content={"message": f'Error running query.'})
    except Exception as e:
        print(f"Error running query: {e}")
        raise
        return JSONResponse(status_code=500, content={"message": f'Error running query.'})
    
async def delete_image(
    background_tasks: BackgroundTasks,
    project_id: str,
    file_id: str):
    
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Deleting file {file_id} from {project_id} database.')

        background_tasks.add_task(delete_image_data, project_id, file_id)

        return JSONResponse(status_code=200, content={"message": f'File deleted successfully.'})
    except Exception as e:
        print(f"Error deleting file: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'_id': file_id}
        update = {"$set" : {'status': 'success'}}
        collection.update_one(query, update)
        return JSONResponse(status_code=500, content={"message": f'Error deleting file.'})
        
    