from flask import Flask, jsonify, request, Response
from flask_restful import Api
from flask_jwt_extended import JWTManager
from datetime import timedelta
from dotenv import load_dotenv
from flask_cors import CORS
import os
import logging
from logging.handlers import RotatingFileHandler

load_dotenv()

from src.extensions import mongo, redis_client
from src.auth.routes import auth_bp
from src.apps.routes import apps_bp
from src.analytics.routes import analytics_bp
import src.utils.decorators as decorators

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True, automatic_options=True)

    mongo.init_app(app)
    redis_client.init_app(app)
    jwt = JWTManager(app)

    decorators.init_limiter(app)

    # Logging
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/easicrypt_ussd.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('EasiCrypt USSD startup now')

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(apps_bp, url_prefix='/api/apps')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')

    @app.route('/', methods=['GET'])
    @decorators.limiter.exempt
    def home():
        return jsonify({"message": "Welcome to EasiCrypt"}), 200

    @app.route('/ussd', methods=['POST'])
    @decorators.limiter.limit("100 per minute")
    def ussd_entry_point():
        from src.ussd.services import handle_ussd_request
        return handle_ussd_request(request)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return Response("END Service busy, please try again in a moment.", mimetype="text/plain", status=429)

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({"message": "Internal server error"}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)