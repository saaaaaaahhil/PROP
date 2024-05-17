from connections.mongo_db import mongodb_client
from config import Config
import os
# from bson.objectid import ObjectId


def get_project_data(project_id: str, category: str):
    """
    This function takes project_id and the category of query for eg. healthcare/landmark and returns data from the metadata database.
    """
    try:
        db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
        collection = db[str(os.environ['MONGO_META_COLLECTION'])]

        selection = {'_id': project_id} 
        projection = {f'{category}' : 1, '_id': 0}

        data = collection.find_one(selection, projection)
        return data
    
    except Exception as e:
        print(f'Error in retrieving the data from database: {e}')
        raise


