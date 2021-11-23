from flask import Blueprint

from src.views.auth.auth import general_auth_api

auth_apis = Blueprint('auth_apis', __name__)
auth_apis.register_blueprint(general_auth_api)
