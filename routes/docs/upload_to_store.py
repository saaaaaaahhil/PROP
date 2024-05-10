from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
from threading import Lock
import PyPDF2
import re
import uuid
import numpy as np
from io import BytesIO

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
    try:
        print(f"Uploading document {file_name} to index {project_id}...")
        index_client = get_index_client(project_id)
        if index_client:
            docs = chunkify_document(project_id, contents, file_type, file_name)
            index_client.upload_documents(docs)
            print(f"Document uploaded successfully.")
            return {"success": True, "message": "Document uploaded successfully."}
        else:
            raise Exception("Error retrieving search index client.")
            return {"success": False, "message": "Error retrieving search index client."}
    except Exception as e:
        print(f"Error uploading document to index: {e}")
        raise
        return {"success": False, "message": f"Error uploading document to index: {e}"}
        