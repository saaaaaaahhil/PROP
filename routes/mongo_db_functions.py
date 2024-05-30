from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from connections.mongo_db import file_collection, meta_collection
from config import Config
from routes.exceptions import RetryableException

# Retry configuration
RETRY_WAIT = wait_exponential(multiplier=int(Config.RETRY_MULTIPLIER), min=int(Config.RETRY_MIN), max=int(Config.RETRY_MAX))
RETRY_ATTEMPTS = int(Config.RETRY_ATTEMPTS)


@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def update_mongo_file_status(query: dict, update: dict, upsert_val=False):
    try:
        file_collection.update_one(query, update, upsert_val)
        return True
    except Exception as e:
        raise RetryableException(f'Error updating file status: {e}')


@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_file(file_id : str, project_id: str):
    """
    This function returns the file document from Mongo DB based on file_id and project_id.
    """
    try:
        return file_collection.find_one({'_id': file_id, 'project_id': project_id})
    except Exception as e:
        raise RetryableException(f'Error getting file: {e}')

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def delete_file_from_mongo(file_id: str, project_id: str):
    """
    This function takes file_id and project_id and remove file from database.
    """
    try: 
        return file_collection.delete_one({'_id': file_id, 'project_id': project_id})
    except Exception as e:
        raise RetryableException(f'Error deleting file from mongodb: {e}')

@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_project_metadata(project_id: str, category: str):
    """
    This function takes project_id and the category of query for eg. healthcare/landmark and returns data from the metadata database.
    """
    try:
        selection = {'_id': project_id} 
        projection = {f'{category}' : 1, '_id': 0}

        data = meta_collection.find_one(selection, projection)
        return {'success': True, 'answer': data}
    
    except Exception as e:
        print(f'Error in retrieving the data from database: {e}')
        raise RetryableException(f'Error in retrieving the data from database: {e}')


@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def get_project_files(project_id: str):
    """
    This function will return all the files stored for current project.
    """
    try:
        response = []
        selection = {'project_id': project_id}
        projection = {'_id': 1, 'file_name': 1, 'file_type' : 1, 'file_size': 1, 'added_on' : 1, 'status' : 1}
        data = file_collection.find(selection, projection)

        for doc in data:
            response.append(doc)
        
        return {'success': True, 'answer' : response}
    
    except Exception as e:
        print(f"Failed to retrieve the data: {e}")
        raise RetryableException(f"Failed to retrieve the data: {e}")


@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def check_file_exist(query, projection ={}):
    """
    This function takes filename and project_id as input and checks if file exists in database.
    """
    try:
        check = file_collection.find_one(query, projection)
        if check is not None:
            return check
        return None
    except Exception as e:
        print("Status check failed")
        raise RetryableException(f"Status check failed: {e}")


def update_project_version(project_id: str):
    """
    This function updates the version number of project whenever file is uploaded or deleted.
    """
    try:
        pass
        # check = project_collection.find_one({'_id': project_id})
        # if check is not None:
        #     current_version = check['version']
        #     project_collection.update_one({'_id': project_id}, {'$set':{'version': (current_version+1)%100}})
        #     return {'success': True}
        # project_collection.update_one({'_id': project_id}, {'$set':{'version': 0}}, upsert=True)
        # return {'success': True}
    except Exception as e:
        print(f'Error updating project version: {e}')
        raise e
    
def get_project_version(project_id: str):
    """
    This function returns a project version.
    """
    try:
        # check = project_collection.find_one({'_id': project_id})
        # if check is None:
        #     raise Exception(f'{project_id} not found.')
        # return check['version']
        return 1
    except Exception as e:
        print(f'Error getting project version: {e}')
        raise e
    
@retry(stop=stop_after_attempt(RETRY_ATTEMPTS), wait=RETRY_WAIT, retry=retry_if_exception_type(RetryableException))
def insert_metadata_to_db(vicinity_map):
    try:
        result = meta_collection.insert_one(vicinity_map)
        print(result)
    except Exception as e:
        print(f'Error uploading metadata: {e}')
        raise RetryableException(f'Error uploading location metadata into mongodb: {e}')

        