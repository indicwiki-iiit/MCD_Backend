from flask import Flask
from flask_cors import CORS

from src.views.auth import auth_apis
from src.views.tasks import task_apis
from src.views.questions import question_apis
from src.views.responses import response_apis
from src.views.users import user_apis, leaderboard_api
from src.views import connection_apis


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config['CORS_HEADERS'] = 'Content-Type'

    app.register_blueprint(connection_apis)
    app.register_blueprint(auth_apis)
    app.register_blueprint(task_apis)
    app.register_blueprint(question_apis)
    app.register_blueprint(response_apis)
    app.register_blueprint(user_apis)
    app.register_blueprint(leaderboard_api)

    return app
