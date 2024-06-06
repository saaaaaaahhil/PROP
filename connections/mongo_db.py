from pymongo import MongoClient
from config import Config

try:
    mongodb_client = MongoClient(Config.MONGO_DB_URI)
    db = mongodb_client[str(Config.MONGO_DB_DATABASE)]
    file_collection = db[str(Config.MONGO_FILE_COLLECTION)]
    meta_collection = db[str(Config.MONGO_META_COLLECTION)]
    # project_collection = db[str(Config.MONGO_PROJECT_COLLECTION)]
    chat_collection = db[str(Config.MONGO_CHAT_COLLECTION)]
    debug_collection = db[str(Config.MONGO_DEBUG_COLLECTION)]
except Exception as e:
    print(f"MongoDB connection unsuccessfull: {e}")
    raise