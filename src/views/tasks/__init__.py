from flask import Blueprint

from src.views.tasks.tasks import general_task_api
from src.views.tasks.task_generic import task_generic_api
from src.views.tasks.task_report import task_report_api

task_apis = Blueprint('task_apis', __name__, url_prefix='/task')

task_apis.register_blueprint(general_task_api)
task_apis.register_blueprint(task_generic_api)
task_apis.register_blueprint(task_report_api)
