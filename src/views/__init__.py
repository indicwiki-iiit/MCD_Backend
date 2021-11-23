import src.database as db
from flask import Blueprint
from src.utils import json_response

connection_apis = Blueprint('connection_apis', __name__)


@connection_apis.route("/", methods=["GET"])
def server_status():
    return json_response({"status": "micro-content-development backend is running."})


# This route gives error!!
@connection_apis.route("/status/", methods=["GET"])
def db_connection_status():
    connections = db.mongo_db.command("serverStatus")["connections"]
    # status_collection = mongo_db.status.find_one({})
    # text = status_collection['text'] if len(
    #     status_collection) else 'Not connected.'
    return json_response({"status": connections})
