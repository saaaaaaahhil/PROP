from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

import asyncio
from starlette.concurrency import run_in_threadpool

from fastapi import BackgroundTasks

import PyPDF2
import logging
from io import BytesIO
from config import Config
from routes.docs.store_operations import upload_document_to_index, delete_doc_data
from routes.docs.search import run_rag_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/doc', tags=['DOC'])

async def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    project_id: str,
    id: str):

    try:
        if file.content_type != 'application/pdf':
            return JSONResponse(status_code=400, content={"message": f'File format for {file.filename} not supported, please upload a PDF file.'})

        logger.info(f'Uploading file {file.filename} to {project_id} index.')

        file_type = file.content_type
        file_name = file.filename
        contents = await file.read()

        background_tasks.add_task(upload_document_to_index, project_id, contents, file_name, file_type)
        return {'success': True}
    except Exception as e:
        logger.info(f'Error uploading file: {e}')
        raise
        return JSONResponse(status_code=500, content={"message": f'Error uploading file.'})
        
    
@router.post('/run_doc_query')
async def run_doc_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        logger.info(f'Running query for project {project_id}...')

        response = await run_in_threadpool(run_rag_pipeline, project_id, query)
        if response["success"]:
            return JSONResponse(status_code=200, content={"message": f'Query ran successfully.', "result": response["answer"]})
        else:
            return JSONResponse(status_code=500, content={"message": f'Error running query.'})
    except Exception as e:
        logger.info(f"Error running query: {e}")
        return JSONResponse(status_code=500, content={"message": f'Error running query.'})
        raise
    
async def delete_doc(
    background_tasks: BackgroundTasks,
    project_id: str,
    file_id: str):

    try:
        logger.info(f'Deleting file {file_id} from {project_id} database.')

        background_tasks.add_task(delete_doc_data, project_id, file_id)
        
        return {'success': True}
    except Exception as e:
        logger.info(f"Error deleting file: {e}")
        raise
        return JSONResponse(status_code=500, content={"message": f'Error deleting file.'})
    