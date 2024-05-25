from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient

from threading import Lock

from config import Config
import logging
from routes.docs.create_index import create_or_update_index

index_clients = {}
index_locks = {}
global_lock = Lock()


def get_lock(project_id):

    global global_lock, index_locks
    # Ensure thread safety while accessing the index_locks dictionary
    with global_lock:
        if project_id not in index_locks:
            index_locks[project_id] = Lock()
        return index_locks[project_id]
    
def get_index_client(project_id):
    """
    This function retrieves the search index client for the specified project ID.
    """
    try:
        with get_lock(project_id):
            # Check if the index client already exists
            if project_id in index_clients:
                return index_clients[project_id]

            try:
                # Get the search service endpoint and key from the environment
                service_endpoint = Config.AZURE_SEARCH_SERVICE_ENDPOINT
                key = Config.AZURE_SEARCH_API_KEY

                # Create the search index client
                client = SearchIndexClient(service_endpoint, AzureKeyCredential(key))
                client.get_index(project_id)
            except ResourceNotFoundError:
                # Create the index if it does not exist
                create_or_update_index(project_id)

            index_client = SearchClient(service_endpoint, project_id, AzureKeyCredential(key))
            index_clients[project_id] = index_client
            return index_client
    except Exception as e:
        print(f"Error retrieving search index client: {e}")
        raise
        return None