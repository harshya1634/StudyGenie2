import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


load_dotenv()


class MongoNotAvailable(RuntimeError):
    pass


def get_db():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "studygenie")
    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=2500,
        connectTimeoutMS=2500,
        socketTimeoutMS=2500,
    )
    return client[db_name]


def get_db_checked():
    db = get_db()
    try:
        db.client.admin.command("ping")
    except ServerSelectionTimeoutError as e:
        raise MongoNotAvailable(
            "MongoDB is not reachable. Start MongoDB or update MONGODB_URI in .env"
        ) from e
    return db

