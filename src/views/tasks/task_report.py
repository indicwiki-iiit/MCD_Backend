import json

from bson import ObjectId, json_util
from flask import Blueprint, request

import src.database as db
from src.models import Task
from src.utils import json_response, get_questions_with_responses_from_task_query, \
    get_user_with_token

task_report_api = Blueprint('task_report_api', __name__)


@task_report_api.route("/<string:task_id>/report/", methods=["GET"])
def get_task_report(task_id):
    creator_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    # Checking whether user is admin/problem-setter or not
    if not creator_details or creator_details['user_type'] not in ['problem_setter', 'admin']:
        return json_response({'error': 'not permitted.'}, status=401)
    task_id = task_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)
    task_id = ObjectId(task_id)  # Retrieving the task id

    task_filter = {'_id': task_id}
    pipeline = get_questions_with_responses_from_task_query(task_filter) + [
        {"$unwind": "$responses"},
        {"$lookup": {  # add user details for each user response
            "from": "user",
            "let": {"uoid": {"$toObjectId": "$responses.user_id"}},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$_id", "$$uoid"]}}},
                {"$project": {"email": 1, "first_name": 1, "last_name": 1}}
            ],
            "as": "responses.user",
        }},
        {"$unwind": "$responses.user"},
        {"$project": {"_id": 1, "name": 1, "question_list": 1, "responses": 1}},
        {"$project": {
            "question_list.review_flag": 0,
            "question_list.question_contexts": 0,
            "responses.user._id": 0
        }}  # removing un-necessary attributes
    ]
    res = db.mongo_db.task.aggregate(pipeline)
    if not res:
        return json_response({'error': 'no annotations found for the provided task.'}, status=404)

    # after using json_util, $oid field is added in user
    res = json.loads(json_util.dumps(list(res), indent=2))
    for resp in res:  # Removing that for easy access of ids
        resp["_id"] = resp["_id"]["$oid"]
        resp["responses"]["_id"] = resp["responses"]["_id"]["$oid"]
        resp["responses"]["response"] = " ".join(resp["responses"]["response"])
    return json_response({"status": "success", "response": res})


@task_report_api.route("/creator/", methods=["GET"])
def get_creator_tasks():
    creator_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    # Checking whether user is admin/problem-setter or not
    if not creator_details or creator_details['user_type'] not in ['problem_setter', 'admin']:
        return json_response({'error': 'not permitted.'}, status=401)

    user_id = str(creator_details["_id"])
    filter_by_user = {}
    # Give admin access to get report for any task but restrict problem-setter
    if creator_details['user_type'] != 'admin':
        user_id = user_id.strip()
        filter_by_user.update({"problem_setter_id": user_id})

    # Getting those tasks
    res = db.mongo_db.task.find(filter_by_user, {'details': 0, 'question_list': 0})

    tasks = []
    for t in res:
        task = Task(**t).to_json()
        task.pop('details')
        task.pop('question_list')
        tasks.append(task)

    print(tasks, user_id)
    return json_response({"status": "success", "response": tasks})
