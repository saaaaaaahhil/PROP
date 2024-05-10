from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
from starlette.concurrency import run_in_threadpool
from io import BytesIO
import pandas as pd
from threading import Lock

from routes.csv.upload_to_sql import upload_to_sql
from routes.csv.sql_agent_test import run_test_query
from routes.csv.sql_agent import run_query

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

@router.post('/upload_data')
async def upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...)):

    try:
        project_lock = await get_project_lock(project_id)
        async with project_lock:
            print(f'Uploading file {file.filename} to {project_id} database.')
            if not(file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
                return JSONResponse(status_code=400, content={"message": f'File format for {file.filename} not supported, please upload a CSV or XLSX file.'})

            contents = await file.read()
            # Check the file extension to determine the format
            if file.filename.endswith('.csv'):
                # Convert CSV string to DataFrame for preview/processing
                df = await read_csv_async(contents)
            else:
                # Use pandas to read the XLSX file from bytes
                df = await read_xlsx_async(contents)

            df.columns = [c.lower().replace(' ', '_') for c in df.columns]

            # remove extension from filename, make lowercase, and replace spaces with underscores
            file_name = file.filename.split('.')[0].lower().replace(' ', '_')

            background_tasks.add_task(upload_to_sql, project_id, df, file_name)
            return JSONResponse(status_code=200, content={"message": f'File {file.filename} uploaded successfully to {project_id} database.'})
    except Exception as e:
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
