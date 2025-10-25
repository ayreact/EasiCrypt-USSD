from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, unset_jwt_cookies
from src.auth import auth_bp
from src.auth.services import register_developer, login_developer, reset_developer_password
from src.extensions import mongo
from flask_cors import cross_origin 
import logging

log = logging.getLogger(__name__)

@auth_bp.route('/signup', methods=['POST'])
@cross_origin(origins=["http://localhost:8080"], supports_credentials=True, methods=['POST']) 
def signup():
    log.info(f"Signup route hit. Method: {request.method}, URL: {request.url}")
    log.info(f"Request headers: {request.headers}")
    log.info(f"Is JSON: {request.is_json}")

    if not request.is_json:
        log.error("Signup POST request received without application/json Content-Type.")
        return jsonify({"message": "Request must be JSON"}), 415

    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"message": "Missing required fields"}), 400

    try:
        developer_id = register_developer(username, email, password)
        return jsonify({"message": "Developer created successfully", "developer_id": developer_id}), 201
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An error occurred during signup", "error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not all([email, password]):
        return jsonify({"message": "Missing email or password"}), 400

    try:
        developer = login_developer(email, password)
        access_token = create_access_token(identity=str(developer['_id']))
        refresh_token = create_refresh_token(identity=str(developer['_id']))
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 401
    except Exception as e:
        return jsonify({"message": "An error occurred during login", "error": str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('new_password')

    if not all([email, new_password]):
        return jsonify({"message": "Missing email or new password"}), 400

    try:
        reset_developer_password(email, new_password)
        return jsonify({"message": "Password reset successfully"}), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An error occurred during password reset", "error": str(e)}), 500