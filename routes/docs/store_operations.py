from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2
import docx
import re
import uuid
import numpy as np
from io import BytesIO
from config import Config
from routes.docs.embeddings import get_embeddings
from routes.docs.index_search_client import get_index_client
import logging
from routes.mongo_db_functions import update_mongo_file_status, delete_file_from_mongo, get_file, update_project_version

def read_docx(contents):
    try:
        data = ""
        doc = docx.Document(BytesIO(contents))
        for paragraph in doc.paragraphs:
            data += paragraph.text + "\n"
        data = re.sub(r'\s+', ' ', data).strip()
        return data
    except Exception as e:
        print(f"Error reading DOCX file: {e}")
        raise

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
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        data = read_docx(contents)
    else:
        raise Exception("Invalid file type. Only PDF or DOCX files are supported.")

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
    file_uploaded_to_storage = False 
    try:
        print(f"Uploading document {file_name} to index {project_id}...")

        chunks_id = []
        file_size = len(contents) / 1024

        index_client = get_index_client(project_id)
        if index_client:
            #Get document chunks
            docs = chunkify_document(project_id, contents, file_type, file_name)
            
            #Get unique id's of chunks created
            for doc in docs:
                chunks_id.append(doc['id'])


            index_client.upload_documents(docs)
            print(f"Document uploaded successfully.")
            file_uploaded_to_storage = True

            
            #Update project version
            # update_project_version(project_id)

            #Update File Status to 'success'
            query = {'file_name': file_name, 'project_id': project_id}
            update = {"$set": {'file_size': f'{round(file_size,1)} KB', 'chunks':chunks_id, "status": 'success'}}
            update_mongo_file_status(query, update)
            
            return {"success": True, "message": "Document uploaded successfully."}
        else:
            raise Exception("Error retrieving search index client.")
    
    except Exception as e:
        print(f"Error uploading document to index: {e}")
        if file_uploaded_to_storage == False:
            update_mongo_file_status({'file_name': file_name, 'project_id': project_id}, {'$set': {'status': 'fail'}})
        raise
        
def delete_doc_data(project_id: str, file_id: str):
    """
    This function takes container_name and blob_name to delete blob from Azure Blob Storage.
    """
    try:
        print(f'Deleting file {file_id} from {project_id} database.')

        #Get filename from metadata
        file = get_file(file_id, project_id)
        if file is None:
            raise Exception('File Not Found.')
        
        chunk_list = file['chunks']
        
        # Create a batch of delete actions for each document ID
        documents = [{"id": document_id} for document_id in chunk_list]
        index_client = get_index_client(project_id)
        if index_client:
            #Delete file from storage.
            result = index_client.delete_documents(documents)
            if result[0].succeeded:
                print("Documents deleted successfully.")

                #Update project version
                update_project_version(project_id)

                #Delete file from metadata.
                result = delete_file_from_mongo(file_id, project_id)
                if result.acknowledged:
                    return {'success': True, "message": f'File {file_id} deleted successfully from {project_id}'}
            else:
                #Revert file delete status to 'success' in case of failure
                update_mongo_file_status({'_id': file_id, 'project_id': project_id}, {'$set' : {'status': 'success'}})
                print("Failed to delete documents:", result[0].error)
                return {"success": False, "answer": "Failed to delete file!"}
        else:
            raise Exception("Error retrieving search index client.")
        
    except Exception as e:
        print(f"Failed to delete file {file_id} from project {project_id}: {e}")
        #Revert file delete status to 'success' in case of failure
        update_mongo_file_status({'_id': file_id, 'project_id': project_id}, {'$set' : {'status': 'success'}})
        raise
