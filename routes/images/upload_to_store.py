from routes.images.blob_storage_operations import get_container_client

def upload_image_to_store(project_id, contents, file_name, file_type):
    """
    This function uploads a file to Azure Blob Storage.
    """
    try:
        if file_type not in ['image/jpeg', 'image/png']:
            print(f'File format for {file_name} not supported, please upload a JPEG or PNG image.')
            return {"success" : False, "message" : f'File format for {file_name} not supported, please upload a JPEG or PNG image.'}

        print(f"Uploading file {file_name} to Azure Blob Storage {project_id}...")
        container_client = get_container_client(project_id)
        container_client.upload_blob(name=file_name, data=contents, overwrite=True)
        print(f"File {file_name} uploaded successfully.")
        
        return {"success" : True, "message" : f"File {file_name} uploaded successfully."}
    except Exception as e:
        print(f"Error uploading file to Azure Blob Storage: {e}")
        raise
        return {"success" : False, "message" : f"Error uploading file to Azure Blob Storage: {e}"}