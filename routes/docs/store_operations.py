from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
from threading import Lock
import PyPDF2
import re
import uuid
import numpy as np
from io import BytesIO

from connections.mongo_db import mongodb_client

from config import Config
from routes.docs.embeddings import get_embeddings
from routes.docs.index_search_client import get_index_client

def read_pdf(contents):
    data = ""
    pdf = PyPDF2.PdfReader(BytesIO(contents))
    for page in pdf.pages:
        data += page.extract_text()
    data = re.sub(r'\s+', ' ', data).strip()
    return data

def chunkify_document(project_id, contents, file_type, file_name):
    """
    This function splits a document into chunks of text.
    """
    print(f"Chunkifying document {file_name} for project {project_id}.")
    data = ""
    if file_type == "application/pdf":
        data = read_pdf(contents)
    else:
        raise Exception("Invalid file type. Only PDF files are supported.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=Config.RAG_CHUNK_SIZE, chunk_overlap=Config.RAG_CHUNK_OVERLAP, length_function=len, is_separator_regex=False)
    embeddings = get_embeddings()
    docs = []
    # Split the documents into smaller chunks
    for chunk in text_splitter.split_text(data):
        embedding = embeddings.embed_query(chunk)
        docs.append({"id": str(uuid.uuid4()), "content": chunk, "content_vector": np.array(embedding, dtype=np.float32).tolist(), "project_id": project_id, "source": file_name})
    print(f"Document chunkified into {len(docs)} chunks.")
    return docs

def upload_document_to_index(project_id, contents, file_name, file_type):
    """
    This function uploads a document to the search index.
    """
    id = str(uuid.uuid4())

    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f"Uploading document {file_name} to index {project_id}...")

        chunks_id = []
        collection = db[str(Config.MONGO_DB_COLLECTION)]

        index_client = get_index_client(project_id)
        if index_client:
            docs = chunkify_document(project_id, contents, file_type, file_name)
            
            for doc in docs:
                chunks_id.append(doc['id'])

            query = {'file_name': file_name}
            update = {"$set": {'chunks':chunks_id, "status": 'success'}}
            collection.update_one(query, update)

            index_client.upload_documents(docs)
            print(f"Document uploaded successfully.")
            print(f'No of documents present are: {index_client.get_document_count()}')
            return {"success": True, "message": "Document uploaded successfully."}
        else:
            raise Exception("Error retrieving search index client.")
    
    except Exception as e:
        print(f"Error uploading document to index: {e}")
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        query = {'file_name': file_name}
        update = {"$set": {"status": 'fail'}}
        collection.update_one(query, update)
        raise
        

def delete_doc_data(project_id: str, file_id: str):
    """
    This function takes container_name and blob_name to delete blob from Azure Blob Storage.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Deleting file {file_id} from {project_id} database.')
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        #Get filename from metadata
        chunks = collection.find_one({'_id': file_id},{'chunks': 1})
        if chunks is None:
            return {"success": False, "answer": "File Not Found !"}
        
        chunk_list = chunks['chunks']
        # Create a batch of delete actions for each document ID
        documents = [{"id": document_id} for document_id in chunk_list]
        index_client = get_index_client(project_id)
        if index_client:
            result = index_client.delete_documents(documents)
            if result[0].succeeded:
                print("Documents deleted successfully.")
                result = collection.delete_one({"_id" : file_id})
                if result.acknowledged:
                    print(f'Documents present after deletion: {index_client.get_document_count()}')
                    return {'success': True, "message": f'File {file_id} deleted successfully from {project_id}'}
            else:
                update_store_delete_status(db, file_id, 'success')
                print("Failed to delete documents:", result[0].error)
                return {"success": False, "answer": "Failed to delete file!"}
        else:
            raise Exception("Error retrieving search index client.")
        
    except Exception as e:
        print(f"Failed to delete file {file_id} from project {project_id}: {e}")
        update_store_delete_status(db, file_id, 'success')
        raise


def update_store_delete_status(db, file_id, status):
    collection = db[str(Config.MONGO_DB_COLLECTION)]
    query = {'_id': file_id}
    update = {"$set": {"status": status}}
    collection.update_one(query, update)
    return True