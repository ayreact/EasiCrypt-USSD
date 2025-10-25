from flask import request, jsonify
from src.analytics import analytics_bp
from src.analytics.services import get_app_metrics
from src.utils.decorators import app_owner_required
from bson.objectid import ObjectId

@analytics_bp.route('/<string:app_id>', methods=['GET'])
@app_owner_required()
def get_metrics(app_id):
    if not ObjectId.is_valid(app_id):
        return jsonify({"message": "Invalid App ID"}), 400

    try:
        metrics = get_app_metrics(app_id)
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({"message": "Error retrieving metrics", "error": str(e)}), 500