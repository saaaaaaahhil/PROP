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
from connections.mongo_db import mongodb_client
import routes.query_router.router as query_router
import redis
from config import Config
import uuid
from datetime import datetime

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


@app.post('/upload_file')
async def upload_file(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file: UploadFile = File(...)):
    """
    This function takes the project_id and file to be uploaded.
    """
    id = str(uuid.uuid4())
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Uploading file {file.filename} to {project_id} database.')
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ["csv", "pdf", "jpg", "jpeg", "png", "xlsx"]:
            return JSONResponse(status_code=400, content={"message": f'Invalid file format: {file_extension}.'})
        
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        check = collection.find_one({'file_name': file.filename})
        if check is not None:
            if check['status'] == 'success':
                print("File already exists in database !")
                return JSONResponse(status_code=400, content={"message": f'File {file.filename} already exists in database.'})
            else:
                id = check['_id']

        #Get file size
        contents = await file.read()
        file_size_kb = len(contents) / 1024  # Convert size to KB
        await file.seek(0)

        query = {"_id": id}
        update = {"$set": {'file_name': file.filename,'project_id': project_id, 'file_type': file_extension, 'file_size': f'{round(file_size_kb,1)} KB' , "added_on": datetime.now().isoformat(),'chunks' : [], 'status' : 'in_progress'}}
        collection.update_one(query, update, upsert=True)
  
        upload_routes = {
            'xlsx': upload_data,
            'csv': upload_data,
            'pdf': upload_doc,
            'jpg': upload_image,
            'jpeg': upload_image,
            'png' : upload_image
        }

        response = await upload_routes[file_extension](background_tasks, file, project_id, id)
        return response
    except Exception as e:
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'_id': id}
        update = {"$set": {"status": "fail"}}
        collection.update_one(query,update,upsert=True)
        return JSONResponse(status_code=500, content={"message": f'Error uploading file {file.filename} to {project_id} database: {e}'})

    
@app.post('/delete_file')
async def delete_file(
    background_tasks: BackgroundTasks,
    project_id: str = Form(...),
    file_id: str = Form(...)):
    """
    This function takes project_id and file_id and deletes file from project database.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Deleting file {file_id} from {project_id} database.')

        collection = db[str(Config.MONGO_DB_COLLECTION)]


        file_type = collection.find_one({'_id': file_id},{'file_type': 1})
        if file_type is None:
            return JSONResponse(status_code=400, content={"message": "Incorrect file_id."})

        delete_routes = {
            'xlsx' : delete_data,
            'csv'  : delete_data,
            'pdf'  : delete_doc,
            'jpeg' : delete_image,
            'jpg'  : delete_image,
            'png'  : delete_image
        }
        
        query = {'_id': file_id}
        update = {"$set" : {'status': 'deleting'}}
        collection.update_one(query, update)

        response = await delete_routes[file_type['file_type']](background_tasks, project_id, file_id)
        return response
    except Exception as e:
        print(f"Error deleting file: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'_id': file_id}
        update = {"$set" : {'status': 'success'}}
        collection.update_one(query, update)
        return JSONResponse(status_code=500, content={"message": f'Error deleting the file: {file_id}'})


def get_project_files(project_id: str):
    """
    This function will return all the files stored for current project.
    """

    try:
        db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        response = []
        selection = {'project_id': project_id}
        projection = {'_id': 1, 'file_name': 1, 'file_type' : 1, 'file_size': 1, 'added_on' : 1, 'status' : 1}
        data = collection.find(selection, projection)

        for doc in data:
            response.append(doc)
        
        return {'success': True, 'answer' : response}
    
    except Exception as e:
        print(f"Failed to retrieve the data: {e}")
        raise


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)