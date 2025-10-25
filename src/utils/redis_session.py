from src.extensions import redis_client
import json

class USSDSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self._key = f"ussd:session:{session_id}"
        self.client = redis_client.get_client()

    def get(self):
        """Retrieves the session data."""
        data = self.client.get(self._key)
        return json.loads(data) if data else None

    def set(self, data, expire_seconds=3600): # Session expires after 1 hour
        """Sets or updates the session data."""
        self.client.setex(self._key, expire_seconds, json.dumps(data))

    def delete(self):
        """Deletes the session."""
        self.client.delete(self._key)

    def exists(self):
        """Checks if the session exists."""
        return self.client.exists(self._key)