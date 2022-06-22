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
    master_blueprint = Blueprint('master_blueprint', __name__, url_prefix='/api')

    master_blueprint.register_blueprint(connection_apis)
    master_blueprint.register_blueprint(auth_apis)
    master_blueprint.register_blueprint(task_apis)
    master_blueprint.register_blueprint(question_apis)
    master_blueprint.register_blueprint(response_apis)
    master_blueprint.register_blueprint(user_apis)
    master_blueprint.register_blueprint(leaderboard_api)
    app.register_blueprint(master_blueprint)
    print(app.url_map)
    return app
