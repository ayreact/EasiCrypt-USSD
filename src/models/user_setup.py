from src.extensions import mongo
from bson.objectid import ObjectId
from datetime import datetime

class UserSetup:
    @staticmethod
    def _get_collection():
        if mongo.db is None:
            raise RuntimeError("MongoDB connection not initialized. Ensure app.init_app(app) is called.")
        return mongo.db.user_setups

    @staticmethod
    def create(phone_number, app_id, encrypted_code, hashed_pin):
        setup_data = {
            "phone_number": phone_number,
            "app_id": app_id,
            "encrypted_code": encrypted_code,
            "hashed_pin": hashed_pin,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = UserSetup._get_collection().insert_one(setup_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_phone_and_app(phone_number, app_id):
        return UserSetup._get_collection().find_one({"phone_number": phone_number, "app_id": app_id})

    @staticmethod
    def update_pin(setup_id, new_hashed_pin):
        UserSetup._get_collection().update_one(
            {"_id": ObjectId(setup_id)},
            {"$set": {"hashed_pin": new_hashed_pin, "updated_at": datetime.utcnow()}}
        )
        return True