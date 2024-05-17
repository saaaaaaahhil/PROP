from pymongo import MongoClient
from config import Config

try:
    mongodb_client = MongoClient(Config.MONGO_DB_URI)
except Exception as e:
    print(f"MongoDB connection unsuccessfull: {e}")
    raise