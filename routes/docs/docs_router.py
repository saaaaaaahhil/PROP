from fastapi import APIRouter
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from fastapi import BackgroundTasks
from routes.docs.store_operations import upload_document_to_index, delete_doc_data
from routes.docs.search import run_rag_pipeline
from routes.docs.store_images import upload_image

router = APIRouter(prefix='/doc', tags=['DOC'])

async def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    project_id: str,
    id: str):

    try:
        if file.content_type != 'application/pdf' and file.content_type != 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return JSONResponse(status_code=400, content={"message": f'File format for {file.filename} not supported, please upload a PDF or a DOCX file.'})

        print(f'Uploading file {file.filename} to {project_id} index.')

        file_type = file.content_type
        file_name = file.filename
        contents = await file.read()

        background_tasks.add_task(upload_document_to_index, project_id, contents, file_name, file_type)
        background_tasks.add_task(upload_image, contents, project_id)

        return {'success': True}
    except Exception as e:
        print(f'Error uploading file: {e}')
        return {'success': True, 'failure': f'Failed to upload docx/pdf data: {e}'}
    
@router.post('/run_doc_query')
async def run_doc_query(
    project_id: str = Form(...),
    query: str = Form(...)):

    try:
        print(f'Running query for project {project_id}...')

        response = await run_in_threadpool(run_rag_pipeline, project_id, query)
        if response["success"]:
            return JSONResponse(status_code=200, content={"message": f'Query ran successfully.', "result": response["answer"]})
        else:
            return JSONResponse(status_code=500, content={"message": f'Error running query.'})
    except Exception as e:
        print(f"Error running query: {e}")
        return JSONResponse(status_code=500, content={"message": f'Error running query.'})
        raise
    
async def delete_doc(
    background_tasks: BackgroundTasks,
    project_id: str,
    file_id: str):

    try:
        print(f'Deleting file {file_id} from {project_id} database.')

        background_tasks.add_task(delete_doc_data, project_id, file_id)
        
        return {'success': True}
    except Exception as e:
        print(f"Error deleting file: {e}")
        return {'success': False, 'failure': f'Failure in deleting doc: {e}'}
