import os
from datetime import timedelta

class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/easicrypt_ussd')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key-please-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-super-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    EASICRYPT_WALLET_API = os.getenv('EASICRYPT_WALLET_API', 'https://easicrypt-wallet.onrender.com')
    # Rate limit configuration
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '100 per minute'