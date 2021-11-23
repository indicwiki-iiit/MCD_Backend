from bson import ObjectId
from flask import Blueprint, request

import src.database as db
from src.utils import json_response, get_user_with_token, get_number, \
    get_questions_for_exclusive_session

general_question_api = Blueprint('general_question_api', __name__)


def get_questions_in_range(task_id, question_type, start_index, end_index):
    offset = end_index - start_index + 1
    cmd = db.mongo_db.task.aggregate([
        {"$match": {'_id': task_id}}, {"$unwind": "$question_list"},
        {"$match": {"question_list.question_type": question_type}},
        {"$group": {'_id': '$_id', "question_list": {"$push": "$question_list"}}}
    ], allowDiskUse=True)
    res = [x for x in cmd]
    if len(res) != 1:
        return []
    # one don't need sorting as queslist are inserted on the basis of sequence number
    # but this need verification
    final_res = sorted(res[0]['question_list'], key=lambda x: x['seqno'])[start_index - 1:end_index]
    return final_res


@general_question_api.route("/questions/", methods=["GET"])
def get_question(task_id):
    if request.args.get('auth_token', None):
        end_user = get_user_with_token(
            db.mongo_db, request.args.get('auth_token', ''))
        if not end_user:
            return json_response({'error': 'user not found.'}, status=404)
    else:
        return json_response({'error': 'not permitted.'}, status=401)

    # check whether question_type is present in the request arguments or not
    question_type = request.args.get('question_type', None)
    if not question_type:
        return json_response({'error': 'question type not provided'}, status=400)

    user_id = str(end_user['_id'])
    start_index = request.args.get('start_index', None)
    end_index = request.args.get('end_index', None)

    if not start_index or not end_index:
        return json_response({"error": "invalid start_index and end_index specified."}, status=400)

    start_index, end_index = get_number(start_index), get_number(end_index)
    # checking type of start_index and end_index
    if not start_index or not end_index:
        return json_response(
            {"error": "start_index and end_index are of invalid types. It must be integer."},
            status=400)

    if start_index > end_index:
        return json_response({"error": "start_index must be less than end_index."}, status=400)

    # only updates the question list if question_list field is present
    task_id = task_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)

    task_object_id = ObjectId(task_id)
    task_rows = db.mongo_db.task.find(
        {'_id': task_object_id}, {'question_list': 0})
    if not task_rows:
        return json_response({'error': 'task not found.'}, status=404)

    task_collection_list = [x for x in task_rows]
    if len(task_collection_list) != 1:
        return json_response({'error': 'multiple tasks found.'}, status=400)

    task_collection = task_collection_list[0]
    # return list of question within the start and end range that are sorted by seqno
    final_question_list = get_questions_in_range(
        task_object_id, question_type, start_index, end_index)
    if len(final_question_list) == 0:
        return json_response({'status': 'success', 'response': final_question_list})

    # getting the annotations
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id, "user_id": user_id,
         "question_id": {"$in": [x['id'] for x in final_question_list]}})
    annotation_map = {x['question_id']: x for x in annotation_row}
    for x in final_question_list:
        if x['id'] in annotation_map:
            x['user_response'] = annotation_map[x['id']]['response']
            x['annotation_done'] = True
        else:
            x['user_response'] = []
            x['annotation_done'] = False

    return json_response({'status': 'success', 'response': {
        'questions': {int(i): x for i, x in enumerate(final_question_list)},
        'question_count': len(final_question_list), 'task_name': task_collection['name']}})


@general_question_api.route("/single_view_questions/", methods=["GET"])
def get_single_view_question(task_id):
    if request.args.get('auth_token', None):
        end_user = get_user_with_token(
            db.mongo_db, request.args.get('auth_token', ''))
        if not end_user:
            return json_response({'error': 'user not found.'}, status=404)
    else:
        return json_response({'error': 'not permitted.'}, status=401)

    user_id = str(end_user['_id'])
    session_index = request.args.get('session_index', None)

    if not session_index:
        return json_response({"error": "session_index is not specified."}, status=400)

    session_index = get_number(session_index)
    # checking type of session_index
    if session_index is None:
        return json_response({"error": "session_index is of invalid types. It must be integer."},
                             status=400)

    # only updates the question list if question_list field is present
    task_id = task_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)

    task_object_id = ObjectId(task_id)
    task_rows = db.mongo_db.task.find_one({'_id': task_object_id}, {
        '_id': 0, 'question_list': 0})
    if not task_rows:
        return json_response({'error': 'task not found.'}, status=404)

    final_question_list = get_questions_for_exclusive_session(
        task_object_id, user_id, session_index=session_index)
    if len(final_question_list) == 0:
        return json_response({'status': 'failure',
                              'response': 'No questions here, Please go back to the task page.'})

    # getting the annotations
    print('\n\n1.calling db.response.find with:', '\ntask_id:', task_id, '\nuser_id:', user_id,
          '\nqIDs:', [x['id'] for x in final_question_list])
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id, "user_id": user_id,
         "question_id": {"$in": [x['id'] for x in final_question_list]}})
    annotation_map = {x['question_id']: x for x in annotation_row}
    print('\n\n1.annotation_map before:', annotation_map)
    for x in final_question_list:
        if x['id'] in annotation_map:
            x['user_response'] = annotation_map[x['id']]['response']
            x['annotation_done'] = True
        else:
            x['user_response'] = []
            x['annotation_done'] = False
    print('\n\n1.annotation_map after:', annotation_map)

    return json_response({'status': 'success', 'response': {
        'questions': {int(i): x for i, x in enumerate(final_question_list)},
        'question_count': len(final_question_list), 'task_name': task_rows['name']}})
