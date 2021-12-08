import json
from collections import defaultdict

from bson import ObjectId, json_util
from flask import Blueprint, request

import src.database as db
from src.utils import json_response, get_questions_with_responses_from_task_query, question_counts, \
    get_user_with_token, get_questions_for_exclusive_session, get_number

session_questions_api = Blueprint('session_questions_api', __name__)


# Route to get questions and general_response_api for a given task_api id, session id and user id
# This route was colliding with some previous route so changed it
@session_questions_api.route("/session/<string:session_id>/questions/", methods=["GET"])
def get_task_questions(task_id, session_id):
    user_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not user_details:  # Checking for authorized user
        return json_response({'error': 'not permitted.'}, status=401)

    user_id = str(user_details["_id"])
    user_id = user_id.strip()
    task_id = task_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)
    task_id = ObjectId(task_id)  # Retrieving the task id

    session_id = int(session_id)
    task_filter = {'_id': task_id}
    pipeline = get_questions_with_responses_from_task_query(task_filter) + [
        {"$match": {'question_list.session_id': session_id, 'question_list.assigned': user_id}},
    ]
    # Get all questions and their responses based on session and task_id
    res = db.mongo_db.task.aggregate(pipeline)
    if not res:
        return json_response({'error': 'no questions found for the provided task.'}, status=404)
    res = json.loads(json_util.dumps(res, indent=2))

    # Removing all the $oid parameters added in ids
    for q in res:
        q["_id"] = q["_id"]["$oid"]
        for r in q["responses"]:
            r["_id"] = r["_id"]["$oid"]

    # Adding count fields in one single object
    data = {
        "single_view_stats": question_counts(task_filter),
        "questions": res
    }
    return json_response({"status": "success", "response": data})


# Releases single question from the user
@session_questions_api.route("/question_release/<string:question_id>/", methods=["POST"])
def question_release(task_id, question_id):
    print("\nINSIDE SINGLE_RELEASE API\n")
    user_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not user_details:  # Checking for authorized user
        return json_response({'error': 'not permitted.'}, status=401)

    user_id = str(user_details["_id"])
    user_id = user_id.strip()

    task_id_str = task_id.strip()
    if not ObjectId.is_valid(task_id_str):
        return json_response({'error': 'task not found.'}, status=404)
    task_id = ObjectId(task_id_str)
    question_id = question_id.strip()

    # check whether question is already annotated or not
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id_str, "user_id": user_id, "question_id": question_id})
    annotation_row = [x for x in annotation_row]
    if (len(annotation_row)):
        return json_response({"error": 'Question is already annotated'}, status=404)

    question_pipe = [{"$match": {"_id": task_id}},
                     {"$unwind": "$question_list"},
                     {"$match": {"question_list.id": question_id,
                                 "question_list.assigned": user_id}}]
    # print(question_pipe)
    question_data = db.mongo_db.task.aggregate(question_pipe)
    question_data = [x for x in question_data]

    print(">>", question_data)

    if len(question_data) == 0:
        return json_response({"error": 'No question found with the given id'}, status=404)

    if len(question_data) > 1:
        return json_response({"error": 'Multiple questions found with the given id'}, status=400)

    prev_session_id = question_data[0]['question_list']['session_id']
    task_name = question_data[0]['name']

    # update the existing document
    # also checking wether question is blocked by the given user or not.
    res = db.mongo_db.task.update_one(
        {"_id": task_id, "question_list.id": question_id, "question_list.assigned": user_id},
        {"$set": {"question_list.$.session_id": 0, "question_list.$.assigned": ''}}
    )
    if res.matched_count <= 0:  # If no document was found by the query
        return json_response({"error": 'No question found with the given id'})

    updated_questions = get_questions_for_exclusive_session(task_id, user_id,
                                                            session_id=prev_session_id)
    if len(updated_questions) == 0:
        return json_response({'status': 'failure',
                              'response': 'You have deleted all questions in this session. Please go back to the task page.'})
    # getting the annotations
    print('\n\n2.calling db.response.find with:', '\ntask_id:', task_id, '\nuser_id:', user_id,
          '\nqIDs:', [x['id'] for x in updated_questions])
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id_str, "user_id": user_id,
         "question_id": {"$in": [x['id'] for x in updated_questions]}})
    annotation_map = {x['question_id']: x for x in annotation_row}
    print('\n\n2.annotation_map before:', annotation_map)
    for x in updated_questions:
        if x['id'] in annotation_map:
            x['user_response'] = annotation_map[x['id']]['response']
            x['annotation_done'] = True
        else:
            x['user_response'] = []
            x['annotation_done'] = False
    print('\n\n2.annotation_map after:', annotation_map)

    response = {
        # sending the updated questions
        'questions_count': len(updated_questions),
        'questions': {int(i): x for i, x in enumerate(updated_questions)},
        "task_name": task_name
    }
    # print('releaseResponse:', response)
    return json_response({"status": "success", "response": response})


# Releases bulk questions from the user
@session_questions_api.route("/bulk_question_release/", methods=["POST"])
def bulk_question_release(task_id):
    print("\nINSIDE BULK_RELEASE API\n")
    user_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not user_details:  # Checking for authorized user
        return json_response({'error': 'not permitted.'}, status=401)

    user_id = str(user_details["_id"])
    user_id = user_id.strip()

    task_id_str = task_id.strip()
    if not ObjectId.is_valid(task_id_str):
        return json_response({'error': 'task not found.'}, status=404)
    task_id = ObjectId(task_id_str)
    release_question_data = request.get_json()
    question_ids = release_question_data.get('question_ids', [])

    if len(question_ids) == 0:
        return json_response({"error": 'No question provided !!!'}, status=404)
        # check whether question is already annotated or not
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id_str, "user_id": user_id, "question_id": {"$in": question_ids}})
    annotation_row = [x for x in annotation_row]
    if len(annotation_row):
        return json_response({"error": 'Question is already annotated'}, status=404)

    question_pipe = [{"$match": {"_id": task_id}},
                     {"$unwind": "$question_list"},
                     {"$match": {"question_list.id": {"$in": question_ids},
                                 "question_list.assigned": user_id}}]
    # print(question_pipe)
    question_data = db.mongo_db.task.aggregate(question_pipe)
    question_data = [x for x in question_data]

    if len(question_data) == 0:
        return json_response({"error": 'No question found with the given id'}, status=404)

    prev_session_id = question_data[0]['question_list']['session_id']
    task_name = question_data[0]['name']

    res = db.mongo_db.task.update_many(
        {"_id": task_id},
        {"$set": {"question_list.$[ques].session_id": 0,
                  "question_list.$[ques].assigned": ''}
         },
        upsert=False, array_filters=[{"ques.id": {"$in": question_ids}}]
    )

    updated_questions = get_questions_for_exclusive_session(task_id, user_id,
                                                            session_id=prev_session_id)
    if len(updated_questions) == 0:
        return json_response({'status': 'failure',
                              'response': 'You have deleted all questions in this session. Please go back to the task page.'})
    # getting the annotations
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id_str, "user_id": user_id,
         "question_id": {"$in": [x['id'] for x in updated_questions]}})
    annotation_map = {x['question_id']: x for x in annotation_row}
    for x in updated_questions:
        if x['id'] in annotation_map:
            x['user_response'] = annotation_map[x['id']]['response']
            x['annotation_done'] = True
        else:
            x['user_response'] = []
            x['annotation_done'] = False

    response = {
        # sending the updated questions
        'questions_count': len(updated_questions),
        'questions': {int(i): x for i, x in enumerate(updated_questions)},
        "task_name": task_name
    }
    # print('releaseResponse:', response)
    return json_response({"status": "success", "response": response})


# Request to get the question stats for the single-view task
@session_questions_api.route("/single_view_stats/", methods=["GET"])
def request_single_view_stats(task_id):
    task_id = ObjectId(task_id)
    task_filter = {"_id": task_id}
    return json_response(question_counts(task_filter))


# Request Question for a task_api
@session_questions_api.route("/request_questions/", methods=["POST"])
def request_questions(task_id):
    user_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not user_details:  # Checking for authorized user
        return json_response({'error': 'not permitted.'}, status=401)

    # Taking required data
    user_id = str(user_details["_id"])
    user_id = user_id.strip()
    question_count = get_number(request.args.get('session_length', 0))
    # if question count is not a valid number
    if question_count is None or question_count == 0:
        return json_response({'error': 'invalid sesssion_length is specified.'}, status=400)
    task_id_str = task_id.strip()
    if not ObjectId.is_valid(task_id_str):
        return json_response({'error': 'task not found.'}, status=404)
    task_id = ObjectId(task_id_str)

    res = db.mongo_db.task.aggregate([
        {"$match": {"_id": task_id, "access_type": 'single-view'}},
        # Filtering all questions which were assigned to user or unassigned
        {"$project": {"question_list": {
            "$filter": {
                "input": "$question_list",
                "as": "questions",
                "cond": {"$or": [
                    {"$eq": ["$$questions.assigned", ""]},
                    {"$eq": ["$$questions.assigned", user_id]}
                ]}
            }
        }}},
        # Calculating the new session id by taking out max
        {"$project": {"question_list": 1, "max_session_id": {"$max": "$question_list.session_id"}}},
        {"$unwind": "$question_list"},
        # Removing assigned questions
        {"$match": {"question_list.assigned": ""}},
        # Taking unassigned questions with max limit described in question_count
        {"$limit": question_count},
        # Grouping them back
        {"$group": {"_id": "$_id",
                    "max_session_id": {"$max": "$max_session_id"},
                    "questions": {"$push": "$question_list"}}
         }
    ])
    res = json.loads(json_util.dumps(res, indent=2))
    if not res:
        return json_response({'error': 'There are no more questions left to solve.'}, status=404)
    res = res[0]
    new_session_id = res["max_session_id"] + 1
    # Getting question id for all questions which will be assigned to the user
    questions_ids = [x["id"] for x in res["questions"]]
    res["_id"] = res["_id"]["$oid"]

    # Updating all entries of questions which are taken about by aggregate
    updated_data = db.mongo_db.task.update_many(
        {"_id": task_id},
        {"$set": {"question_list.$[ques].session_id": new_session_id,
                  "question_list.$[ques].assigned": user_id}
         },
        array_filters=[{"ques.id": {"$in": questions_ids}}]
    )

    if updated_data.matched_count <= 0:  # If no document was found by the query
        return json_response({"error": 'Something went wrong'})

        # also update the session progress
    question_collection = db.mongo_db.task.find_one({'_id': task_id}, {
        '_id': 0, 'question_list.seqno': 1, 'question_list.id': 1, 'question_list.assigned': 1,
        'question_list.session_id': 1})
    # handling for single-view task
    global_question_ids = set()
    question_session_grouping = defaultdict(lambda: set())
    for qdata in question_collection['question_list']:
        if qdata['assigned'] != user_id:
            continue
        question_session_grouping[qdata['session_id']].add(qdata['id'])
        global_question_ids.add(qdata['id'])
    annotation_row = db.mongo_db.response.find(
        {"task_id": task_id_str, "user_id": user_id,
         "question_id": {"$in": list(global_question_ids)}}, {"_id": 0, "question_id": 1})
    annotation_list = set([x['question_id'] for x in annotation_row])
    user_progress = []
    for k, v in sorted(question_session_grouping.items(), key=lambda x: x[0]):
        local_session_progress = (len((v.intersection(annotation_list))) / float(len(v))) * 100
        user_progress.append(round(local_session_progress, 2))
    session_progress = {"Exclusive Questions": user_progress}

    task_filter = {"_id": task_id}
    response = {
        "questions": res,
        "single_view_stats": question_counts(task_filter),
        "session_progress": session_progress
    }
    return json_response({"status": "success", "response": response})
