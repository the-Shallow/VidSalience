from pymongo import MongoClient
from app.config import settings


mongo_client = MongoClient(settings.MONGO_URI)

db = mongo_client[settings.DB_NAME]

jobs_collection = db["jobs"]
