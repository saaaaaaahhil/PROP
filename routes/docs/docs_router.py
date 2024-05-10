from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

import asyncio
from starlette.concurrency import run_in_threadpool

from fastapi import BackgroundTasks

import PyPDF2
import re
from io import BytesIO

from routes.docs.upload_to_store import upload_document_to_index
from routes.docs.search import run_rag_pipeline

router = APIRouter(prefix='/doc', tags=['DOC'])

@router.post('/upload_doc')
async def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...)):

    try:
        if file.content_type != 'application/pdf':
            return JSONResponse(status_code=400, content={"message": f'File format for {file.filename} not supported, please upload a PDF file.'})

        print(f'Uploading file {file.filename} to {project_id} index.')

        file_type = file.content_type
        file_name = file.filename
        contents = await file.read()

        background_tasks.add_task(upload_document_to_index, project_id, contents, file_name, file_type)
        return JSONResponse(status_code=200, content={"message": f'File uploaded successfully.'})
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise
        return JSONResponse(status_code=500, content={"message": f'Error uploading file.'})
    
@router.post('/run_doc_query')
async def run_doc_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        print(f'Running query for project {project_id}...')

        response = await run_in_threadpool(run_rag_pipeline, project_id, query)
        if response["success"]:
            return JSONResponse(status_code=200, content={"message": f'Query ran successfully.', "response": response["answer"]})
        else:
            return JSONResponse(status_code=500, content={"message": f'Error running query.'})
    except Exception as e:
        print(f"Error running query: {e}")
        raise
        return JSONResponse(status_code=500, content={"message": f'Error running query.'})