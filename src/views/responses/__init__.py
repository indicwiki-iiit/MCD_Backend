from flask import Blueprint
from src.views.responses.response import general_response_api

response_apis = Blueprint('response_apis', __name__,
                          url_prefix='/task/<string:task_id>/annotation/<string:question_id>')

response_apis.register_blueprint(general_response_api)
