from src.extensions import mongo
from bson.objectid import ObjectId
from datetime import datetime

class App:
    @staticmethod
    def _get_collection():
        if mongo.db is None:
            raise RuntimeError("MongoDB connection not initialized. Ensure app.init_app(app) is called.")
        return mongo.db.apps

    @staticmethod
    def create(developer_id, app_name):
        app_data = {
            "developer_id": developer_id,
            "app_name": app_name,
            "visible": False,
            "endpoints": {
                "verify_endpoint": None,
                "send_endpoint": None,
                "get_balance_endpoint": None,
                "off_ramp_endpoint": None
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = App._get_collection().insert_one(app_data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_id(app_id):
        return App._get_collection().find_one({"_id": ObjectId(app_id)})

    @staticmethod
    def find_by_developer_id(developer_id):
        return list(App._get_collection().find({"developer_id": developer_id}))

    @staticmethod
    def update(app_id, update_data):
        update_data["updated_at"] = datetime.utcnow()
        App._get_collection().update_one(
            {"_id": ObjectId(app_id)},
            {"$set": update_data}
        )
        return True

    @staticmethod
    def delete(app_id):
        App._get_collection().delete_one({"_id": ObjectId(app_id)})
        return True

    @staticmethod
    def get_visible_apps():
        return list(App._get_collection().find({"visible": True}))
