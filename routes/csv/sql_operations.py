from routes.csv.connect_db import get_or_create_database
import pandas as pd
from connections.mongo_db import mongodb_client
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from config import Config


def update_mongo_upload_status(db, original_filename, status):
    collection = db[str(Config.MONGO_DB_COLLECTION)]
    query = {'file_name': original_filename}
    update = {"$set": {"status": status}}
    collection.update_one(query, update)
    return True


def update_mongo_delete_status(db, file_id, status):
    collection = db[str(Config.MONGO_DB_COLLECTION)]
    query = {'_id': file_id}
    update = {"$set": {"status": status}}
    collection.update_one(query, update)
    return True


def upload_to_sql(project_id: str, df: pd.DataFrame, filename: str, original_filename: str):
    """
    This function takes a DataFrame and uploads it to a SQL database.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f"Uploading DataFrame to SQL database {project_id}...")
        
        # Get the database engine
        engine = get_or_create_database(project_id)

        # Upload the DataFrame to the database
        df.to_sql(filename, engine, if_exists='replace', index=False)
        
        # Update the uploaded file's details in files metadata
        update_mongo_upload_status(db, original_filename, 'success')

        print("File Uploaded successfully")
        return True
    
    except Exception as e:
        update_mongo_upload_status(db, original_filename, 'fail')
        print(f"Error uploading DataFrame to SQL: {e}")
        raise


def delete_data_sql(project_id: str, file_id: str):
    """
    This function takes a project_id and file_id and deletes file from database.
    """
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    try:
        print(f'Deleting file from {project_id} database.')
    
        collection = db[str(Config.MONGO_DB_COLLECTION)]
        
        #Get filename from metadata
        file_name = collection.find_one({'_id': file_id},{'file_name': 1})
        if file_name is None:
            return {"success": False, "answer": "File Not Found !"}
        
        table_name = file_name['file_name'].split('.')[0].lower().replace(' ', '_')


        # Get the database engine
        engine = get_or_create_database(project_id)
        Base = declarative_base()
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = metadata.tables[table_name]
        if table is not None:
            Base.metadata.drop_all(engine, [table], checkfirst=True)

        result = collection.delete_one({'_id': file_id})
        if result.acknowledged:
            print("File deleted successfully.")
            return {'success': True}
        else:
            raise Exception("Failed to delete metadata")
        
    except Exception as e:
        update_mongo_delete_status(db, file_id, 'success')
        print(f'Failed to delete file {file_id} from database {project_id}: {e}')
        raise

