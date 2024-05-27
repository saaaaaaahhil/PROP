from connections.azure_blob_storage import blob_service_client
from config import Config
import re

def get_blob_url(blob_name: str, project_id: str):
    container_name = sanitize_container_name(project_id)
    blob_url = Config.AZURE_BLOB_STORAGE_BASE_URL + "/" + container_name + "/" + blob_name
    print(blob_url)
    return blob_url

def get_image_urls(project_id: str):
    """
    This function returns a list of URLs for images stored in Azure Blob Storage.
    """
    try:
        container_client = get_container_client(project_id)
        blob_list = container_client.list_blobs()
        urls = [get_blob_url(blob.name, project_id) for blob in blob_list]
        return {"success" : True, "urls" : urls}
    except Exception as e:
        print(f"Error getting image URLs from Azure Blob Storage: {e}")
        raise
        return {"success" : False, "message" : f"Error getting image URLs from Azure Blob Storage: {e}"}

def sanitize_container_name(name):
    """
    Sanitize the input string to be compliant with Azure container naming rules.
    """
    # Lowercase, replace invalid characters with '-', and trim to maximum length
    sanitized = re.sub(r"[^a-z0-9]", "-", name.lower())[:63]
    # Ensure the container name starts with a letter or number (Azure rule)
    sanitized = re.sub(r"^-+", "", sanitized)
    # Ensure the container name ends with a letter or number (Azure rule)
    sanitized = re.sub(r"-+$", "", sanitized)
    return sanitized

def get_container_client(project_id):
    container_name = sanitize_container_name(project_id)
    container_client = blob_service_client.get_container_client(container_name)
    if not container_client.exists():
        container_client.create_container(public_access="container")
    return container_client
