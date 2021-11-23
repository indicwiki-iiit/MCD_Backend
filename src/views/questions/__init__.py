from flask import Blueprint
from src.views.questions.questions import general_question_api
from src.views.questions.session_questions import session_questions_api

question_apis = Blueprint('question_apis', __name__, url_prefix='/task/<string:task_id>')

question_apis.register_blueprint(general_question_api)
question_apis.register_blueprint(session_questions_api)
