from routes.images.blob_storage_operations import get_container_client
from connections.mongo_db import mongodb_client
from config import Config
import logging
from routes.mongo_db_functions import update_mongo_file_status, get_file ,delete_file_from_mongo, update_project_version
from PIL import Image
from io import BytesIO

def upload_image_to_store(project_id, contents, file_name, file_type):
    """
    This function uploads a file to Azure Blob Storage.
    """
    file_uploaded_to_storage = False 
    try:
        if file_type not in ['image/jpeg', 'image/png']:
            print(f'File format for {file_name} not supported, please upload a JPEG or PNG image.')
            return {"success" : False, "message" : f'File format for {file_name} not supported, please upload a JPEG or PNG image.'}
        
        print(f"Uploading file {file_name} to Azure Blob Storage {project_id}...")
        # old_file_name = file_name
        # # If the file is a PNG, convert it to JPEG
        # if file_type == 'image/png':
        #     image = Image.open(BytesIO(contents))
        #     with BytesIO() as output:
        #         image.convert("RGB").save(output, format="JPEG")
        #         contents = output.getvalue()
        #     file_name = file_name.rsplit('.', 1)[0] + '.jpeg'
        #     file_type = 'image/jpeg'

        file_size = len(contents) / 1024

        
        container_client = get_container_client(project_id)
        container_client.upload_blob(name=file_name, data=contents, overwrite=True)
        print(f"File {file_name} uploaded successfully.")
        
        file_uploaded_to_storage = True

        
        #Update project version
        update_project_version(project_id)
        
        #Update file upload status to 'success'
        query = {'file_name': file_name, 'project_id': project_id}
        update = {"$set": {'file_size': f'{round(file_size,1)} KB', "status": 'success'}}
        update_mongo_file_status(query, update)

        return {"success" : True, "message" : f"File {file_name} uploaded successfully."}
    
    except Exception as e:
        print(f"Error uploading file to Azure Blob Storage: {e}")
        if file_uploaded_to_storage == False:
            update_mongo_file_status({'file_name': file_name, 'project_id': project_id}, {'$set': {'status': 'fail'}})
        raise e
        return {"success" : False, "message" : f"Error uploading file to Azure Blob Storage: {e}"}
    
def delete_image_data(project_id: str, file_id: str):
    """
    This function takes container_name and blob_name to delete blob from Azure Blob Storage.
    """
    try:
        print(f'Deleting file {file_id} from {project_id} database.')
        
        #Get file from metadata
        file = get_file(file_id, project_id)
        if file is None:
            raise Exception("File not found in database.")
        
        
        blob_name = file['file_name']
        container_client = get_container_client(project_id)
        blob_client = container_client.get_blob_client(blob=blob_name)
        blob_client.delete_blob()

        
        #Update project version
        update_project_version(project_id)

        result = delete_file_from_mongo(file_id, project_id)
        if result.acknowledged:
            print(f"File {blob_name} deleted successfully from project {project_id}.")
            return {"success" : True, "message" : f"File {blob_name} deleted successfully from project {project_id}."}
        else:
            raise Exception('Failed to delete file from metadata.')
            
    except Exception as e:
        print(f"Failed to delete file {file_id} from project {project_id}")
        update_mongo_file_status({'_id': file_id, 'project_id': project_id}, {'$set': {'status': 'success'}})
        raise 
        return {"success": False, "answer": "Failed to delete file!"}

