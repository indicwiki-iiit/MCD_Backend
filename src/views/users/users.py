from flask import Blueprint, request
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from collections import defaultdict
from datetime import datetime

import src.database as db
from src.models import QUESTION_DISP_NAME, User, USER_CRITICAL_FIELDS
from src.utils import json_response, get_time_delta_str, get_proper_date_str, remove_extra_keys, \
    remove_extra_spaces_in_dictionary

user_apis = Blueprint('user_api', __name__, url_prefix='/user/')


def get_user_annotations_details(user_id):
    # getting the lastest annotation details for the user with last modified question type
    query = db.mongo_db.response.aggregate(
        [{"$match": {"user_id": user_id}}, {"$sort": {"date": -1}}, {"$group": {"_id": {
            "task_id": "$task_id", "response_type": "$response_type"},
            "last_modified": {"$first": "$date"}, "count": {"$sum": 1}}}, ], allowDiskUse=True)
    res = [x for x in query]
    user_resp = defaultdict(
        lambda: {'last_modified': '2000-01-01T00:00:00.000000', 'responses': {}})
    for x in res:
        task_id = x['_id']['task_id']
        response_type = QUESTION_DISP_NAME.get(
            x['_id']['response_type'], 'Unknown type')
        user_resp[task_id]['last_modified'] = max(
            str(user_resp[task_id]['last_modified']), str(x['last_modified']))
        user_resp[task_id]['responses'][response_type] = x['count']
    return user_resp


def get_question_count_for_multiple_tasks(task_id_list):
    """
        return number of question present in already exitsing task present in the list. This will thow an error on non-exitsing tasks
        args: task_id_list should be list of valid bson ObjectID
    """
    query = db.mongo_db.task.aggregate(
        [{"$match": {'_id': {"$in": task_id_list}}}, {"$unwind": "$question_list"},
         {"$group": {"_id": {
             "id": "$_id", "question_type": "$question_list.question_type"},
             "task_name": {"$first": "$name"}, "count": {"$sum": 1}}}])
    resp = [x for x in query]
    # grouping the question_type
    task_collections = defaultdict(lambda: {'task_name': '', 'questions': {}})
    for x in resp:
        task_id = str(x['_id']['id'])
        question_type = QUESTION_DISP_NAME.get(
            x['_id']['question_type'], 'Unknown type')
        task_collections[task_id]['task_name'] = x['task_name']
        task_collections[task_id]['questions'][question_type] = x['count']
    return task_collections


def get_problem_setter_activities(user_id):
    query = db.mongo_db.task.find(
        {'problem_setter_id': user_id}, {'question_list': 0})
    res = [x for x in query]

    task_ids = [x['_id'] for x in res]

    task_details = get_question_count_for_multiple_tasks(task_ids)
    # fetch question count in task associated with the problem setter
    task_question_count = {k: sum(
        [qc for _, qc in v['questions'].items()]) for k, v in task_details.items()}

    # get user annotation on the above listed out tasks
    user_response = db.mongo_db.response.aggregate(
        [{"$sort": {"date": -1}}, {"$match": {"task_id": {"$in": [str(x) for x in task_ids]}}}, {
            "$group": {'_id': "$user_id", "task_id": {"$first": "$task_id"},
                       "date_modified": {"$first": "$date"}, "questions": {
                    "$addToSet": "$question_id"}}},
         {"$project": {"task_id": 1, "date_modified": 1, "questions": {"$size": "$questions"}}}],
        allowDiskUse=True)

    task_activity = defaultdict(lambda: {
        'task_name': '', 'last_modified': '', 'user_responses': defaultdict(lambda: 0),
        'task_id': ''})
    for x in user_response:
        task_id = x['task_id']
        questions_done = x['questions']

        task_activity[task_id]['task_name'] = task_details[task_id]['task_name']
        task_activity[task_id]['task_id'] = task_id
        task_activity[task_id]['last_modified'] = max(
            str(task_activity[task_id]['last_modified']), str(x['date_modified']))

        if questions_done == task_question_count[task_id]:
            task_activity[task_id]['user_responses']['completed'] += 1
        else:
            task_activity[task_id]['user_responses']['in-progress'] += 1
        task_activity[task_id]['activity_type'] = "problem creation"
    return task_activity.values()


@user_apis.route('/', methods=['GET'])
def get_all_users():
    all_user_details = db.mongo_db.user.find({})
    res = []
    for x in all_user_details:
        temp_user = User(**x).to_json()
        del temp_user['auth_token']
        res.append(temp_user)
    return json_response({'response': res})


@user_apis.route("/<string:user_id>/", methods=["GET", "PUT"])
def manage_user(user_id):
    user_id = user_id.strip()
    if not ObjectId.is_valid(user_id):
        return json_response({'error': 'user not found.'}, status=404)

    user_object_id = ObjectId(user_id)
    user_row = db.mongo_db.user.find_one({'_id': user_object_id})
    if not user_row:
        return json_response({'error': 'user not found.'}, status=404)

    user_details = User(**user_row).to_json()
    if request.method == 'GET':
        for field in ['auth_token']:
            del user_details[field]
        activity_count = request.args.get('activity_count', 5)
        annotation_details = get_user_annotations_details(user_id)
        task_details = get_question_count_for_multiple_tasks(
            [ObjectId(x) for x in annotation_details])

        # creating recent activity list
        recent_user_activity = []
        # adding overall progress
        overall_progress = {}
        # getting user annotation information
        for task_id, ann_data in annotation_details.items():
            if task_id not in task_details or len(task_details[task_id]['questions']) == 0:
                continue
            activity = {
                'task_id': task_id,
                'activity_type': 'annotation',
                'last_modified': ann_data['last_modified'],
                'task_name': task_details[task_id]['task_name'],
                'annotation_progress': {},
            }
            total_annotations = 0
            total_questions = 0
            for question_type, question_count in task_details[task_id]['questions'].items():
                user_response_count = ann_data['responses'].get(
                    question_type, 0)

                percentage_completed = round((user_response_count / float(question_count)) * 100, 2)
                total_annotations += user_response_count
                total_questions += question_count
                activity['annotation_progress'][question_type] = percentage_completed
            overall_progress[task_details[task_id]['task_name']
            ] = round((total_annotations / float(total_questions)) * 100, 2)
            recent_user_activity.append(activity)

        # getting problem setter activtity details
        if user_details['user_type'] in ['admin', 'problem_setter']:
            recent_user_activity += get_problem_setter_activities(user_id)

        recent_user_activity = sorted(
            recent_user_activity, key=lambda x: x['last_modified'], reverse=True)

        final_activity_list = []
        for x in recent_user_activity[:activity_count]:
            x['last_modified'] = "%s ago" % get_time_delta_str(
                str(x['last_modified']))
            final_activity_list.append(x)

        user_details.update(
            {'recent_activity': final_activity_list})
        user_details['last_active'] = "%s ago" % get_time_delta_str(
            str(user_details['last_active']))
        user_details['date_joined'] = get_proper_date_str(
            user_details['date_joined'])
        user_details['overall_progress'] = overall_progress
        return json_response({'response': user_details})

    end_user_token = request.args.get("auth_token", "")
    if end_user_token.strip() != user_details['auth_token']:
        return json_response({'error': 'not permitted.'}, status=401)

    allowed_fields = ['first_name', 'last_name', 'description']
    curr_user_details = remove_extra_keys(request.get_json(), allowed_fields)

    # check if short description or details are missing
    empty_fields = []
    for field in USER_CRITICAL_FIELDS:
        if field not in curr_user_details:
            continue
        processed_values = curr_user_details[field].strip()
        if len(processed_values) == 0 or processed_values == '':
            empty_fields.append(field)

    if len(empty_fields):
        return json_response({"error": "important fields are empty.", "empty_fields": empty_fields},
                             status=400)

    changed_fields = []
    # check difference in new fields
    for key, value in user_details.items():
        if key not in curr_user_details:
            continue
        else:
            if curr_user_details[key].strip() == value:
                continue
            changed_fields.append(key)

    if len(changed_fields):
        curr_user_details.update({'last_active': datetime.utcnow()})
        # remove extra fields
        curr_user_details, _ = remove_extra_spaces_in_dictionary(
            curr_user_details, allowed_fields)
        curr_user_details = jsonable_encoder(
            curr_user_details, exclude_none=True)
        db.mongo_db.user.update_one({
            "_id": user_object_id,
        }, {
            "$set": curr_user_details
        })

        db.logger.info('>> user details updated : %s | %s fields are changed' % (
            user_details['email'], changed_fields))

    return json_response({'response': 'success'}, status=202)
