from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from config import Config

blob_service_client = BlobServiceClient.from_connection_string(Config.AZURE_BLOB_STORAGE_CONN_STR)