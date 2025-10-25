from flask import request, jsonify
from src.apps import apps_bp
from src.apps.services import create_developer_app, get_developer_apps, update_developer_app, delete_developer_app
from src.utils.decorators import developer_required, app_owner_required
from bson.objectid import ObjectId

@apps_bp.route('/', methods=['POST'])
@developer_required()
def create_app():
    data = request.get_json()
    app_name = data.get('app_name')

    if not app_name:
        return jsonify({"message": "App name is required"}), 400

    try:
        developer_id = str(request.developer['_id'])
        app_id = create_developer_app(developer_id, app_name)
        return jsonify({"message": "App created successfully", "app_id": app_id}), 201
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An error occurred during app creation", "error": str(e)}), 500

@apps_bp.route('/', methods=['GET'])
@developer_required()
def list_apps():
    developer_id = str(request.developer['_id'])
    apps = get_developer_apps(developer_id)
    for app in apps:
        app['_id'] = str(app['_id'])
        app['developer_id'] = str(app['developer_id'])
    return jsonify(apps), 200

@apps_bp.route('/<string:app_id>', methods=['PUT'])
@app_owner_required()
def update_app(app_id):
    if not ObjectId.is_valid(app_id):
        return jsonify({"message": "Invalid App ID"}), 400

    data = request.get_json()
    app_obj = request.app_obj

    endpoints_to_update = {}
    for key in ["verify_endpoint", "send_endpoint", "get_balance_endpoint", "off_ramp_endpoint"]:
        if key in data:
            if data[key] and not (data[key].startswith('http://') or data[key].startswith('https://')):
                return jsonify({"message": f"Invalid URL for {key}"}), 400
            endpoints_to_update[key] = data[key]

    update_fields = {}
    if 'app_name' in data:
        update_fields['app_name'] = data['app_name']
    
    # Logic for 'visible' flag and required endpoints
    if 'visible' in data and isinstance(data['visible'], bool):
        if data['visible'] is True:
            current_endpoints = {**app_obj.get('endpoints', {}), **endpoints_to_update}
            required_endpoints = ["verify_endpoint", "send_endpoint", "get_balance_endpoint"]
            for endpoint_name in required_endpoints:
                if not current_endpoints.get(endpoint_name):
                    return jsonify({"message": f"Cannot set app to visible. '{endpoint_name}' endpoint is required."}), 400
        update_fields['visible'] = data['visible']
    
    if endpoints_to_update:
        update_fields['endpoints'] = {**app_obj.get('endpoints', {}), **endpoints_to_update}


    if not update_fields:
        return jsonify({"message": "No valid fields provided for update"}), 400

    try:
        update_developer_app(app_id, update_fields)
        return jsonify({"message": "App updated successfully"}), 200
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"message": "An error occurred during app update", "error": str(e)}), 500

@apps_bp.route('/<string:app_id>', methods=['DELETE'])
@app_owner_required()
def delete_app(app_id):
    if not ObjectId.is_valid(app_id):
        return jsonify({"message": "Invalid App ID"}), 400

    try:
        delete_developer_app(app_id)
        return jsonify({"message": "App deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "An error occurred during app deletion", "error": str(e)}), 500