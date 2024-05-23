from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
from starlette.concurrency import run_in_threadpool
from io import BytesIO
import pandas as pd
from threading import Lock
import uuid
import logging
from config import Config


from routes.csv.sql_operations import upload_to_sql, delete_data_sql
from routes.csv.sql_agent_test import run_test_query
from routes.csv.sql_agent import run_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix='/csv', tags=['CSV'])

global_lock = asyncio.Lock()
upload_project_locks = {}


async def get_project_lock(project_id):
    async with global_lock:
        if project_id not in upload_project_locks:
            upload_project_locks[project_id] = asyncio.Lock()
    return upload_project_locks[project_id]

async def read_csv_async(contents):
    # Running blocking I/O in an executor
    return await run_in_threadpool(pd.read_csv, BytesIO(contents))

async def read_xlsx_async(contents):
    # Running blocking I/O in an executor
    return await run_in_threadpool(pd.read_excel, BytesIO(contents))

async def upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    project_id: str,
    id: str):
    try:
        project_lock = await get_project_lock(project_id)
        async with project_lock:
            logger.info(f'Uploading file {file.filename} to {project_id} database.')

            #Check file format
            if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
                raise Exception(f'File format for {file.filename} not supported, please upload a CSV or XLSX file.')
            
            contents = await file.read()
            
            # Calculate file size in KB
            file_size = len(contents) / 1024

            if file.filename.endswith('.csv'):
                df = await read_csv_async(contents)
            else:
                df = await read_xlsx_async(contents)

            df.columns = [c.lower().replace(' ', '_') for c in df.columns]

            file_name = file.filename.split('.')[0].lower().replace(' ', '_')
            logger.info(df.head())

            background_tasks.add_task(upload_to_sql, project_id, df, file_name, file.filename, file_size)
            logger.info("Task added to background tasks.")

        return {'success': True}        
    except Exception as e:
        logger.info(f"Exception occurred: {e}")
        raise
        return JSONResponse(status_code=500, content={"message": f'Error uploading file {file.filename} to {project_id} database: {e}'})


# have optional str parameters model and agent_type
@router.post('/run_sql_query_test')
async def run_sql_query(
    project_id: str = Form(...),
    query: str = Form(...),
    model: str = Form("claude-3-sonnet-20240229"),
    agent_type: str = Form("zero-shot-react-description")):

    try:
        # Run the query on the specified database
        response = await run_in_threadpool(run_test_query, project_id, query, model, agent_type)

        if response is None:
            return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database.'})
        else:
            return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', "result": response})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}'})


@router.post('/run_sql_query')
async def run_sql_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        # Run the query on the specified database
        response = await run_in_threadpool(run_query, project_id, query)

        if response is None:
            return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database.'})
        else:
            return JSONResponse(status_code=200, content={"message": f'Query {query} ran successfully on {project_id} database.', "result": response})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f'Error running query {query} on {project_id} database: {e}'})

async def delete_data(
    background_tasks: BackgroundTasks,
    project_id: str,
    file_id: str):

    try:
        project_lock = await get_project_lock(project_id)
        async with project_lock:
            logger.info(f'Deleting file {file_id} from {project_id} database.')
            
            #Delete file from the database in background
            background_tasks.add_task(delete_data_sql, project_id, file_id)

            return {'success': True}

    except Exception as e:
            raise
            return JSONResponse(status_code=500, content={"message": f'Error deleting file {file_id} from {project_id} database: {e}'})


