from datetime import datetime

from bson import ObjectId
from flask import Blueprint, request

import src.database as db
from src.models import Response, QUESTION_LEVELS
from src.utils import json_response, get_user_with_token, question_counts

general_response_api = Blueprint('general_response_api', __name__)


def get_question_by_id(task_id, question_id):
    cmd = db.mongo_db.task.aggregate(
        [{"$match": {'_id': task_id}}, {"$unwind": "$question_list"}, {"$match": {
            "question_list.id": question_id}}])
    res = [x for x in cmd]
    if len(res) != 1:
        if len(res) > 0:
            db.logger.error("multiple questions found with task_id : %s and question_id : %s" % (
                str(task_id), question_id))
        return None

    return res[0]['question_list']


@general_response_api.route("/", methods=["POST"])
def insert_user_response(task_id, question_id):
    end_user = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not end_user:
        return json_response({'error': 'invalid auth_token provided.'}, status=401)

    # only updates the question list if question_list field is present
    task_id = task_id.strip()
    question_id = question_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)

    task_object_id = ObjectId(task_id)
    task_collection = db.mongo_db.task.find_one(
        {'_id': task_object_id}, {'question_list': 0})
    if not task_collection:
        return json_response({'error': 'task not found.'}, status=404)

    # array of size 3 containing the rewards for easy, medium and difficult questions
    task_rewards = task_collection['reward_levels']

    question_data = get_question_by_id(task_object_id, question_id)

    if not question_data:
        return json_response({'error': 'question not found.'}, status=404)

    question_level = question_data.get('question_level', 'medium')

    user_response = request.get_json()
    response = user_response.get('response', None)
    if response:
        if not isinstance(response, list):
            return json_response({'error': 'invalid response format.'}, status=404)
    else:
        response = []
    response_type = user_response.get('response_type', '')
    if response_type != question_data['question_type']:
        return json_response({'error': "question response type didn't match."}, status=400)

    exitsing_response = db.mongo_db.response.find_one(
        {'task_id': task_id, 'question_id': question_id, 'user_id': str(end_user["_id"])})

    response_json = {
        'task_id': task_id,
        'question_id': question_id,
        'user_id': str(end_user["_id"]),
        'response': response,
        'response_type': response_type,
        'date': datetime.utcnow(),
    }

    if exitsing_response:
        _id = db.mongo_db.response.update_one({
            "_id": exitsing_response["_id"],
        }, {
            "$set": response_json
        })
        # checking for single-view questions
        if task_collection.get('access_type', '') == 'single-view':
            single_view_stats = question_counts({'_id': task_object_id})
            return json_response({'response': 'successfully updated exitsing response',
                                  'annotation_id': str(exitsing_response["_id"]),
                                  'single_view_stats': single_view_stats}, status=202)
        else:
            return json_response({'response': 'successfully updated exitsing response',
                                  'annotation_id': str(exitsing_response["_id"])}, status=202)
    else:
        # also credit reward to user
        annotation_score = end_user['annotation_score'] + \
                           task_rewards[QUESTION_LEVELS[question_level]]
        db.mongo_db.user.update_one({"_id": end_user["_id"]}, {"$set": {
            "annotation_score": annotation_score, "last_active": datetime.utcnow()}})
        response_wrapper = Response(**response_json)
        _id = db.mongo_db.response.insert_one(response_wrapper.to_json())
        # checking for single-view questions
        if task_collection.get('access_type', '') == 'single-view':
            single_view_stats = question_counts({'_id': task_object_id})
            return json_response({'response': 'success', 'annotation_id': str(_id.inserted_id),
                                  'single_view_stats': single_view_stats}, status=201)
        else:
            return json_response({'response': 'success', 'annotation_id': str(_id.inserted_id)},
                                 status=201)
