from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from src.extensions import mongo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# placeholder
limiter = None  

def get_phone_number():
    """Use phone number from the USSD request as rate-limit key."""
    data = request.form or request.json or {}
    phone = (
        data.get("phoneNumber")
        or data.get("msisdn")
        or data.get("phone")
        or data.get("sessionId")
    )
    return phone or get_remote_address()

def init_limiter(app):
    """Initialize Flask-Limiter using Redis + phone number keying."""
    global limiter
    limiter = Limiter(
        key_func=get_phone_number,
        default_limits=["100 per minute"],
        storage_uri=app.config["RATELIMIT_STORAGE_URL"]
    )
    limiter.init_app(app)

# --- Authentication decorators ---

def developer_required():
    """Decorator to ensure the user is an authenticated developer."""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            developer = mongo.db.developers.find_one({"_id": current_user_id})
            if not developer:
                return jsonify({"message": "Developer not found"}), 404
            request.developer = developer  # Attach developer object to request
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def app_owner_required(app_id_param='app_id'):
    """Decorator to ensure the developer owns the app."""
    def wrapper(fn):
        @wraps(fn)
        @developer_required()
        def decorator(*args, **kwargs):
            app_id = kwargs.get(app_id_param)
            app = mongo.db.apps.find_one({"_id": app_id, "developer_id": request.developer['_id']})
            if not app:
                return jsonify({"message": "App not found or not owned by developer"}), 403
            request.app_obj = app  # Attach app object to request
            return fn(*args, **kwargs)
        return decorator
    return wrapper
