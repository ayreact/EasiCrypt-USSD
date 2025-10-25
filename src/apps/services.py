from src.models.app import App
from bson.objectid import ObjectId

def create_developer_app(developer_id, app_name):
    app_id = App.create(ObjectId(developer_id), app_name)
    return app_id

def get_developer_apps(developer_id):
    apps = App.find_by_developer_id(ObjectId(developer_id))
    return apps

def update_developer_app(app_id, update_data):
    if not ObjectId.is_valid(app_id):
        raise ValueError("Invalid App ID")
    
    App.update(ObjectId(app_id), update_data)
    return True

def delete_developer_app(app_id):
    if not ObjectId.is_valid(app_id):
        raise ValueError("Invalid App ID")

    App.delete(ObjectId(app_id))
    # TODO:
    return True