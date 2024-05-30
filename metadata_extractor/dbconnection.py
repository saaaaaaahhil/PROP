from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
load_dotenv()


def get_database():

    CONNECTION_STRING = os.getenv("MONGO_DB_URI")
    DB_NAME = os.getenv("MONGO_DB_DATABASE")
    try:
        client = MongoClient(CONNECTION_STRING)
        return client[DB_NAME]
    except: 
        return "Error in connection to DB"

