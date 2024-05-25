from routes.csv.connect_db import get_or_create_database
import pandas as pd
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
import logging
from routes.mongo_db_functions import update_mongo_file_status, get_file, delete_file_from_mongo


def upload_to_sql(project_id: str, df: pd.DataFrame, filename: str, original_filename: str, file_size: float):
    """
    This function takes a DataFrame and uploads it to a SQL database.
    """
    file_uploaded_to_storage = False 
    try:
        print(f"Uploading DataFrame to SQL database {project_id}...")
        
        # Get the database engine
        engine = get_or_create_database(project_id)

        # Upload the DataFrame to the database
        df.to_sql(filename, engine, if_exists='replace', index=False)
        
        file_uploaded_to_storage = True 

        # Update the uploaded file's details in files metadata
        update_mongo_file_status({'file_name': original_filename, 'project_id': project_id},{'$set': {'file_size': f'{round(file_size,1)} KB', 'status': 'success'}})

        print("File Uploaded successfully")
        return True
    
    except Exception as e:
        print(f"Error uploading DataFrame to SQL: {e}")
        # Update the uploaded file's details in files metadata
        if file_uploaded_to_storage == False:
            update_mongo_file_status({'file_name': original_filename, 'project_id': project_id}, {'$set': {'status': 'fail'}})
        raise

def delete_data_sql(project_id: str, file_id: str):
    """
    This function takes a project_id and file_id and deletes file from database.
    """
    try:
        print(f'Deleting file from {project_id} database.')
    
        # Check if file_id and project_id are valid
        file = get_file(file_id, project_id)
        if file is None:
            return {"success": False, "answer": "File Not Found !"}
        
        table_name = file['file_name'].split('.')[0].lower().replace(' ', '_')

        
        # Get the database engine
        engine = get_or_create_database(project_id)
        Base = declarative_base()
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables[table_name]
        if table is not None:
            #Delete file from database
            Base.metadata.drop_all(engine, [table], checkfirst=True)
        else:
            raise Exception('File not found in sql database')
        
        #Delete file from files metadata
        result = delete_file_from_mongo(file_id, project_id)
        if result.acknowledged:
            print("File deleted successfully.")
            return {'success': True}
        else:
            raise Exception("Failed to delete file from metadata")
        
    except Exception as e:
        print(f'Failed to delete file {file_id} from database {project_id}: {e}')
        #Revert status to 'success' in case of failed deletion.
        update_mongo_file_status({'_id': file_id, 'project_id': project_id}, {'$set': {'status': 'success'}})
        raise

