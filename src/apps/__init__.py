from flask import Blueprint

apps_bp = Blueprint('apps', __name__)

from . import routes