import uvicorn
from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import routes.csv.csv_router as csv_router
from routes.csv.csv_router import upload_data, delete_data
from routes.docs.docs_router import upload_doc, delete_doc
from routes.images.images_router import upload_image, delete_image
import routes.docs.docs_router as docs_router
import routes.images.images_router as images_router
import routes.metadata.metadata_router as metadata_router
import routes.query_router.router as query_router
import redis
from config import Config
import uuid
import logging
from datetime import datetime
import time
from routes.mongo_db_functions import get_project_files, check_file_exist, update_mongo_file_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Instantiate Redis
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
    """
    This function takes project_id as input and return all the files uploaded for that project.
    """
    start_time = time.time()
    try:
        # Fetch files for project_id from MongoDB files collection
        response = await run_in_threadpool(get_project_files, project_id)

        #Calculate time to fetch data
        process_time = round(time.time() - start_time, 2)
        if response['success']:
            return JSONResponse(status_code=200, content={"message": f'Files retrieved successfully from {project_id} database.',  'response_time': f'{process_time}s', "result": response['answer']})

        else:
            return JSONResponse(status_code=500, content={"message": f'Error retrieving data for project {project_id}.', 'response_time': f'{process_time}s'})
    except Exception as e:
        process_time = round(time.time() - start_time, 2)
        return JSONResponse(status_code=500, content={"message": f'Error retrieving data from {project_id} database: {e}', 'response_time': f'{process_time}s'})


@app.post('/upload_file')
async def upload_file(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file: UploadFile = File(...)):
    """
    This function takes the project_id and file to be uploaded.
    """
    
    #Generate a unique id for file
    id = str(uuid.uuid4())
    start_time = time.time()
    try:
        logger.info(f'Uploading file {file.filename} to {project_id} database.')

        #Check if file type is supported
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ["csv", "pdf", "jpg", "jpeg", "png", "xlsx"]:
            return JSONResponse(status_code=400, content={"message": f'Invalid file format: {file_extension}.', 'response_time': f'{round(time.time()-start_time,2)}s'})
        
        # Check if file already exists for given project
        check = check_file_exist({'file_name': file.filename, 'project_id': project_id})
        if check is not None:
            if check['status'] == 'success':
                logger.info("File already exists in database !")
                return JSONResponse(status_code=400, content={"message": f'File {file.filename} already exists in database.', 'response_time': f'{round(time.time()-start_time,2)}s'})
            else:
                id = check['_id']

        #Update file upload status to 'in_progress'
        query = {"_id": id, 'project_id': project_id}
        update = {"$set": {'file_name': file.filename, 'file_type': file_extension, 'file_size': f'{0} KB' , "added_on": datetime.now().isoformat(),'chunks' : [], 'status' : 'in_progress'}}
        update_mongo_file_status(query, update, True)
  
        upload_routes = {
            'xlsx': upload_data,
            'csv': upload_data,
            'pdf': upload_doc,
            'jpg': upload_image,
            'jpeg': upload_image,
            'png' : upload_image
        }

        response = await upload_routes[file_extension](background_tasks, file, project_id, id)
        if response['success']:
            return JSONResponse(status_code=200, content={"message": f'File {file.filename} uploaded successfully to {project_id} database.', 'response_time': f'{round(time.time()-start_time,2)}s'})
        else:
            raise
    
    except Exception as e:
        # Update file upload status to 'fail' in case of failure
        update_mongo_file_status({"_id": id, 'project_id': project_id}, {'$set' : {'status': 'fail'}}, True)
        return JSONResponse(status_code=500, content={"message": f'Error uploading file {file.filename} to {project_id} database: {e}', 'response_time': f'{round(time.time()-start_time,2)}s'})

    
@app.post('/delete_file')
async def delete_file(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file_id: str = Form(...)):
    """
    This function takes project_id and file_id and deletes file from project database.
    """
    start_time = time.time()
    try:
        logger.info(f'Deleting file {file_id} from {project_id} database.')

        # Check if file exists for given project_id.
        file = check_file_exist({'_id': file_id, 'project_id': project_id},{'file_type': 1})
        if file is None:
            return JSONResponse(status_code=400, content={"message": "Incorrect file_id.", 'response_time': f'{round(time.time()-start_time,2)}s'})

        delete_routes = {
            'xlsx' : delete_data,
            'csv'  : delete_data,
            'pdf'  : delete_doc,
            'jpeg' : delete_image,
            'jpg'  : delete_image,
            'png'  : delete_image
        }
        
        #Update file delete status to 'deleting'.
        query = {'_id': file_id, 'project_id': project_id}
        update = {"$set" : {'status': 'deleting'}}
        update_mongo_file_status(query, update, False)

        response = await delete_routes[file['file_type']](background_tasks, project_id, file_id)
        if response['success']:
            return JSONResponse(status_code=200, content={"message": f'File {file_id} deleted successfully from {project_id} database.', 'response_time': f'{round(time.time()-start_time,2)}s'})
        else:
            raise

    except Exception as e:
        print(f"Error deleting file: {e}")
        # Restore file delete status to 'success' in case of failure
        update_mongo_file_status({'_id': file_id, 'project_id': project_id}, {"$set" : {'status': 'success'}}, False)
        return JSONResponse(status_code=500, content={"message": f'Error deleting the file: {file_id}', 'response_time': f'{round(time.time()-start_time,2)}s'})

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)