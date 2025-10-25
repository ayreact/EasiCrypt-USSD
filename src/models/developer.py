from src.extensions import mongo
from bson.objectid import ObjectId
from datetime import datetime

class Developer:
    @staticmethod
    def _get_collection():
        if mongo.db is None:
            raise RuntimeError("MongoDB connection not initialized. Ensure app.init_app(app) is called.")
        return mongo.db.developers

    @staticmethod
    def create(username, email, password_hash):
        developer_data = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = Developer._get_collection().insert_one(developer_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_email(email):
        return Developer._get_collection().find_one({"email": email})

    @staticmethod
    def find_by_id(developer_id):
        return Developer._get_collection().find_one({"_id": ObjectId(developer_id)})

    @staticmethod
    def update_password(developer_id, new_password_hash):
        Developer._get_collection().update_one(
            {"_id": ObjectId(developer_id)},
            {"$set": {"password_hash": new_password_hash, "updated_at": datetime.utcnow()}}
        )
        return True