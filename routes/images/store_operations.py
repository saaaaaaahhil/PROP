from routes.images.blob_storage_operations import get_container_client
from connections.mongo_db import mongodb_client
from config import Config


def blobs(blob_list):
    for blob in blob_list:
        print(f"Name: {blob.name}")

def upload_image_to_store(project_id, contents, file_name, file_type):
    """
    This function uploads a file to Azure Blob Storage.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        if file_type not in ['image/jpeg', 'image/png']:
            print(f'File format for {file_name} not supported, please upload a JPEG or PNG image.')
            return {"success" : False, "message" : f'File format for {file_name} not supported, please upload a JPEG or PNG image.'}
        
        print(f"Uploading file {file_name} to Azure Blob Storage {project_id}...")


        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'file_name': file_name}
        update = {"$set": {"status": 'success'}}
        collection.update_one(query, update)
        
        container_client = get_container_client(project_id)
        container_client.upload_blob(name=file_name, data=contents, overwrite=True)
        print(f"File {file_name} uploaded successfully.")
        blobs(container_client.list_blobs())
        return {"success" : True, "message" : f"File {file_name} uploaded successfully."}
    
    except Exception as e:
        print(f"Error uploading file to Azure Blob Storage: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'file_name': file_name}
        update = {"$set": {"status": 'fail'}}
        collection.update_one(query, update)
        return {"success" : False, "message" : f"Error uploading file to Azure Blob Storage: {e}"}
        raise
    

def delete_image_data(project_id: str, file_id: str):
    """
    This function takes container_name and blob_name to delete blob from Azure Blob Storage.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Deleting file {file_id} from {project_id} database.')
        collection = db[str(Config.MONGO_DB_COLLECTION)]

        #Get filename from metadata
        file_name = collection.find_one({'_id': file_id},{'file_name': 1})
        if file_name is None:
            return {"success": False, "answer": "File Not Found !"}
        
        blob_name = file_name['file_name']
        container_client = get_container_client(project_id)
        blob_client = container_client.get_blob_client(blob=blob_name)
        blob_client.delete_blob()

        result = collection.delete_one({"_id" : file_id})
        if result.acknowledged:
            print(f"File {blob_name} deleted successfully from project {project_id}.")
            blobs(container_client.list_blobs())
            return {"success" : True, "message" : f"File {blob_name} deleted successfully from project {project_id}."}
        else:
            raise Exception('Failed to delete file from metadata.')
            
    except Exception as e:
        print(f"Failed to delete file {file_id} from project {project_id}: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'_id': file_id}
        update = {"$set": {"status": 'success'}}
        collection.update_one(query, update)
        return {"success": False, "answer": "Failed to delete file!"}
        raise

