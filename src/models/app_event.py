from src.extensions import mongo
from datetime import datetime

class AppEvent:
    @staticmethod
    def _get_collection():
        if mongo.db is None:
            raise RuntimeError("MongoDB connection not initialized. Ensure app.init_app(app) is called.")
        return mongo.db.app_events

    @staticmethod
    def log_event(event_type, app_id=None, phone_number=None, status=None,
                  message=None, latency_ms=None, metadata=None):
        event_data = {
            "timestamp": datetime.utcnow(),
            "event_type": event_type,
            "app_id": app_id, 
            "phone_number": phone_number, 
            "status": status,
            "message": message,
            "latency_ms": latency_ms,
            "metadata": metadata #
        }
        AppEvent._get_collection().insert_one(event_data)
        return True

    @staticmethod
    def get_events(query, limit=100):
        return list(AppEvent._get_collection().find(query).sort("timestamp", -1).limit(limit))