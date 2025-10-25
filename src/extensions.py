from flask_pymongo import PyMongo
import redis

mongo = PyMongo()

class RedisClient:
    def __init__(self):
        self.client = None

    def init_app(self, app):
        self.client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)

    def get_client(self):
        if not self.client:
            raise RuntimeError("Redis client not initialized. Call init_app first.")
        return self.client

redis_client = RedisClient()