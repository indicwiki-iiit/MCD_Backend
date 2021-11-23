import math
import re
import dateutil.parser
from datetime import datetime
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from flask import Blueprint, request
from collections import defaultdict

import src.database as db
from src.models import Task, QUESTION_DISP_NAME, TASK_CRITICAL_FIELDS, ALL_TASK_FIELDS
from src.utils import *

general_task_api = Blueprint('general_task_api', __name__)

filter_cross_mappings = {
    'tags': 'tags',
    'languages': 'languages',
    'p_id': 'problem_setter_id',
}


def process_filter(filter_args):
    filter_dict = defaultdict(lambda: [])
    for entry in filter_args.split(','):
        temp_data = entry.split(':')
        if len(temp_data) != 2:
            continue
        key, value = temp_data
        filter_dict[key].append(value)
    return filter_dict


def normalize_filter_strings(filter_value):
    filter_value = re.sub(r'\s{1,}', '_', filter_value.strip())
    filter_value = re.sub(':', '', filter_value.lower())
    return filter_value


def apply_filter(filter_dict, res):
    if len(filter_dict) == 0:
        return res

    final_res = res
    invalid_filters = set()
    for key, values in filter_dict.items():
        temp_res = []
        for x in final_res:
            target_key = filter_cross_mappings.get(key, None)
            if not target_key:
                # invalid filter keyword passed
                if key != 'problem_setter':
                    invalid_filters.add(key)
                continue
            target_values = x.get(target_key, [])
            if target_key == 'languages':
                target_values = [REVERSE_LANGUAGE_MAP.get(x, 'unknown') for x in target_values]
            # handle problem setter id differently as this is not a list
            if target_values and target_key == 'problem_setter_id':
                # converting it to list
                target_values = [target_values]
            target_values = set([normalize_filter_strings(x) for x in target_values])
            if len(set(values).intersection(target_values)) == len(values):
                temp_res.append(x)
        final_res = temp_res
    if len(invalid_filters):
        db.logger.debug('invalid filter keyword passed: %s' % invalid_filters)
    return final_res


def get_task_setter():
    """
        return dictionary consists with first name as key and list of user_id
         associated with first name.
    """
    query = db.mongo_db.user.find({'user_type': {"$in": ["admin", "problem_setter"]}},
                                  {'first_name'})
    resp = [x for x in query]
    setter_dict = defaultdict(lambda: [])
    for user_data in resp:
        setter_dict[user_data['first_name']].append(str(user_data['_id']))

    return setter_dict


@general_task_api.route("/tags/", methods=["GET"])
def get_all_tags():
    task_collections = db.mongo_db.task.find(
        {}, {'_id': 0, 'tags': 1, 'languages': 1})
    tag_res = []
    lang_res = []
    for x in task_collections:
        tag_res.extend(x['tags'])
        lang_res.extend(x['languages'])
    tag_res = set(tag_res)
    lang_res = set(lang_res)
    db.logger.debug('successfully fetches %d tags from all the task' %
                    len(tag_res))
    db.logger.debug(
        'successfully fetches %d languages from all the task' % len(lang_res))
    return json_response({'response': {'tags': list(tag_res), 'langs': list(lang_res)}})


@general_task_api.route("/", methods=["GET"])
def get_all_task():
    filter_str = request.args.get('filter', '').strip()
    search_str = request.args.get('search', None)
    sort_str = request.args.get('sort', 'alphabetical')

    filter_dict = {}
    task_setter_dict = get_task_setter()
    if filter_str:
        db.logger.debug('filter string : %s' % filter_str)
        filter_dict = process_filter(filter_str)
        db.logger.debug('filter applied : %s' % filter_dict)
    task_collections = db.mongo_db.task.find(
        {}, {'details': 0, 'question_list': 0})
    res = []
    global_task_setter_ids = set()
    for x in task_collections:
        temp_json = Task(**x).to_json()
        global_task_setter_ids.add(temp_json['problem_setter_id'])
        temp_json['question_count'] = get_question_count(
            ObjectId(temp_json['_id']))
        del temp_json['question_list']
        del temp_json['details']
        temp_json['languages'] = [LANGUAGE_MAP[x]
                                  for x in temp_json['languages'] if x in LANGUAGE_MAP]
        res.append(temp_json)

    db.logger.debug('successfully fetches %d tasks prior filtering' % len(res))
    # extract all the information related to task
    global_filter = {
        'Languages': set(),
        'Tags': set(),
        'Problem Setter': set(),
    }

    # adding question related information
    for x in res:
        for temp in x['languages']:
            global_filter['Languages'].add(temp)
        for temp in x['tags']:
            global_filter['Tags'].add(temp)

    # adding problem setter related information in the filter fields
    normalized_task_setter_dict = defaultdict(lambda: set())
    for user_name, user_ids in task_setter_dict.items():
        temp_user_list = set(user_ids).intersection(global_task_setter_ids)
        if len(temp_user_list) == 0:
            continue
        global_filter['Problem Setter'].add(user_name)
        normalized_task_setter_dict[normalize_filter_strings(user_name)].update(temp_user_list)

    # normalizing the filter keywords
    for ftype, fvalue in global_filter.items():
        # handle languages differently
        normalized_filter_list = [(normalize_filter_strings(x), x) for x in fvalue]
        if ftype == 'Languages':
            normalized_filter_list = [
                (normalize_filter_strings(REVERSE_LANGUAGE_MAP.get(x, 'unknown')), x) for x in
                fvalue]
        global_filter[ftype] = {x[0]: x[1] for x in normalized_filter_list}

    query_ps_ids = set()
    for query_task_setter in filter_dict.get('problem_setter', []):
        if query_task_setter not in normalized_task_setter_dict:
            continue
        query_ps_ids.update(normalized_task_setter_dict[query_task_setter])
    if len(query_ps_ids):
        filter_dict['p_id'] = query_ps_ids
    res = apply_filter(filter_dict, res)

    # applying string searching over the task name
    if search_str:
        search_str = search_str.strip().lower()
        res = [x for x in res if x['name'].strip().lower().startswith(search_str)]

    # sorting by alphabetical or last_modified
    if sort_str.strip().lower() == 'alphabetical':
        res = sorted(res, key=lambda x: x['name'])
    else:
        res = sorted(res, key=lambda x: dateutil.parser.isoparse(x['date_added']))

    db.logger.debug('successfully filtered %d tasks' % len(res))
    return json_response({'response': res, 'filter': global_filter})


# @general_task_api.route("/", methods=["POST"])
# def create_new_task():
#     creator_details = get_user_with_token(
#         db.mongo_db, request.args.get('auth_token', ''))
#     if not creator_details or creator_details['user_type'] not in ['problem_setter', 'admin']:
#         return json_response({'error': 'not permitted.'}, status=401)
#
#     task_details = request.get_json()
#     # updating the problem setter id
#     task_details['problem_setter_id'] = str(creator_details['_id'])
#     # check the missing fields
#     missing_fields = set(TASK_CRITICAL_FIELDS).difference(
#         set(task_details.keys()))
#     if len(missing_fields):
#         return json_response(
#             {'error': 'some critical fields are missing.', 'missing_fields': list(missing_fields)},
#             status=400)
#
#     task_details = remove_extra_keys(task_details, ALL_TASK_FIELDS)
#
#     # check if short description or details are missing
#     empty_fields = []
#     for field in ['name', 'short_description', 'details']:
#         processed_values = task_details[field].strip()
#         if len(processed_values) == 0 or processed_values == '':
#             empty_fields.append(field)
#
#     if len(empty_fields):
#         return json_response({"error": "important fields are empty.", "empty_fields": empty_fields},
#                              status=400)
#
#     # check invalid types
#     is_valid_fields = True
#     for field in ['question_list', 'tags', 'reward_levels']:
#         if field not in task_details:
#             continue
#         if not isinstance(task_details[field], list):
#             is_valid_fields = False
#
#     if not is_valid_fields:
#         return json_response({'error': "field type didn't match."}, status=400)
#
#     # check for existing task with same name
#     exitsing_task = get_existing_task_details(
#         db.mongo_db, task_details['name'].strip())
#     if exitsing_task:
#         return json_response({'error': "task name already exists."}, status=400)
#
#     # check for empty question_list
#     question_list = task_details.get('question_list')
#     if len(question_list) == 0:
#         return json_response({'error': "question_list should contain atleast one question"},
#                              status=400)
#
#     filtered_questions = filter_questions(question_list, db.logger)
#     invalid_questions = len(
#         task_details['question_list']) - len(filtered_questions)
#     languages = set([x.language for x in filtered_questions])
#
#     db.logger.info(
#         'task created by problem_setter: %s with task_name : %s contains %d invalid questions, out of %d total questions across %d languages' % (
#             task_details['problem_setter_id'], task_details['name'], invalid_questions,
#             len(task_details['question_list']), len(languages)))
#     db.logger.info('question langauges are : %s' % languages)
#
#     if len(filtered_questions) == 0:
#         return json_response({'error': "question_list should contain atleast one valid question",
#                               'invalid_question_count': invalid_questions}, status=400)
#
#     task_details.update({'date_added': datetime.utcnow(),
#                          'date_modified': datetime.utcnow(),
#                          'languages': languages,
#                          'question_list': filtered_questions})
#
#     task_collection = Task(**task_details)
#     new_task = db.mongo_db.task.insert_one(task_collection.to_json())
#     db.logger.info('successfully stored the question.')
#     task_ob = task_collection.to_json()
#     task_ob['id'] = str(new_task.inserted_id)
#
#     return json_response({'status': 'success', 'valid_question_count': len(filtered_questions),
#                           'invalid_question_count': invalid_questions, 'task': task_ob}, status=201)


@general_task_api.route("/<string:task_id>/", methods=["GET", "PUT"])
def manage_task(task_id):
    # only updates the question list if question_list field is present
    task_id = task_id.strip()
    if not ObjectId.is_valid(task_id):
        return json_response({'error': 'task not found.'}, status=404)

    task_object_id = ObjectId(task_id)
    task_collection = db.mongo_db.task.find_one(
        {'_id': task_object_id}, {'question_list': 0})
    if not task_collection:
        return json_response({'error': 'task not found.'}, status=404)

    if request.method == 'GET':
        if task_collection.get('access_type', '') != 'single-view':
            question_session_length = request.args.get('session_length', 20)
            question_session_length = get_number(question_session_length)
            if question_session_length is None:
                return json_response(
                    {'error': 'question count per session (session_length) is not an integer.'},
                    status=400)
            if question_session_length <= 0:
                return json_response(
                    {
                        'error': 'question count per session (session_length) must be greater than zero.'},
                    status=400)
        target_task_details = Task(**task_collection).to_json()
        del target_task_details['question_list']

        if request.args.get('auth_token', None):
            end_user = get_user_with_token(
                db.mongo_db, request.args.get('auth_token', ''))
            if not end_user:
                return json_response({'error': 'user not found.'}, status=404)

            if task_collection.get('access_type', '') != 'single-view':
                question_collection = db.mongo_db.task.find_one({'_id': task_object_id}, {
                    '_id': 0, 'question_list.seqno': 1, 'question_list.id': 1,
                    'question_list.question_type': 1})

                # handling for global-view task
                question_grouping = defaultdict(lambda: [])

                for qdata in question_collection['question_list']:
                    disp_name = QUESTION_DISP_NAME.get(
                        qdata['question_type'], 'Unknown type')
                    question_grouping[disp_name].append(qdata)

                # sorting the question by seqno in each group and storing only the question ids
                global_question_ids = []
                for key, value in question_grouping.items():
                    question_grouping[key] = [k['id']
                                              for k in sorted(value, key=lambda x: x['seqno'])]
                    global_question_ids += question_grouping[key]

                target_task_details['question_count'] = {question_type: len(
                    question_ids) for question_type, question_ids in question_grouping.items()}

                annotation_row = db.mongo_db.response.find(
                    {"task_id": task_id, "user_id": str(end_user['_id']),
                     "question_id": {"$in": global_question_ids}}, {"_id": 0, "question_id": 1})
                # using dictionary instead of list for faster retrieval
                annotation_list = set([x['question_id'] for x in annotation_row])

                session_progress = {}
                for question_type, question_ids in question_grouping.items():
                    local_session_progress = []
                    for i in range(math.ceil(target_task_details['question_count'][
                                                 question_type] / question_session_length)):
                        start_index = i * question_session_length
                        end_index = start_index + question_session_length
                        session_span = set(
                            question_grouping[question_type][start_index:end_index])
                        local_session_progress.append(
                            (len((session_span.intersection(annotation_list)))
                             / float(len(session_span))) * 100)
                        session_progress[question_type] = [float("%.2f" % x) if int(
                            x) != x else x for x in local_session_progress]
            else:
                question_collection = db.mongo_db.task.find_one({'_id': task_object_id}, {
                    '_id': 0, 'question_list.seqno': 1, 'question_list.id': 1,
                    'question_list.assigned': 1, 'question_list.session_id': 1})
                # handling for single-view task
                global_question_ids = set()
                question_session_grouping = defaultdict(lambda: set())
                for qdata in question_collection['question_list']:
                    if qdata['assigned'] != str(end_user['_id']):
                        continue
                    question_session_grouping[qdata['session_id']].add(qdata['id'])
                    global_question_ids.add(qdata['id'])
                annotation_row = db.mongo_db.response.find(
                    {"task_id": task_id, "user_id": str(end_user['_id']),
                     "question_id": {"$in": list(global_question_ids)}},
                    {"_id": 0, "question_id": 1})
                annotation_list = set([x['question_id'] for x in annotation_row])
                user_progress = []
                print(question_session_grouping)
                for k, v in sorted(question_session_grouping.items(), key=lambda x: x[0]):
                    local_session_progress = (len((v.intersection(annotation_list))) / float(
                        len(v))) * 100
                    user_progress.append(round(local_session_progress, 2))
                    print(k, round(local_session_progress, 2), len(v))
                session_progress = {"Exclusive Questions": user_progress}
        else:
            target_task_details['question_count'] = get_question_count(
                task_object_id)
            session_progress = {}
            if task_collection.get('access_type', '') != 'single-view':
                for question_type, total_question_count in target_task_details[
                    'question_count'].items():
                    local_session_progress = [
                                                 0] * math.ceil(
                        total_question_count / question_session_length)
                    session_progress[question_type] = local_session_progress
            else:
                # for single-view task club all the questions within single label called Exclusive Questions
                # if user is not logged in then don't display the session details
                session_progress["Exclusive Questions"] = []
        target_task_details['session_progress'] = session_progress
        target_task_details['languages'] = [LANGUAGE_MAP[x]
                                            for x in target_task_details['languages'] if
                                            x in LANGUAGE_MAP]
        target_task_details['date_added'] = get_proper_date_str(
            target_task_details['date_added'])
        target_task_details['date_modified'] = get_time_delta_str(
            target_task_details['date_modified'])
        if task_collection.get('access_type', '') != 'single-view':
            # including backend mapping information for global-view questions
            target_task_details['mapping'] = {
                v: k for k, v in QUESTION_DISP_NAME.items()}
            target_task_details['single_view_stats'] = {}
        else:
            target_task_details['mapping'] = {"Exclusive Questions": 'single-view'}
            single_view_stats = question_counts({'_id': task_object_id})
            target_task_details['single_view_stats'] = single_view_stats
        return json_response({'response': target_task_details})

    end_user = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not end_user or str(end_user['_id']) != task_collection['problem_setter_id']:
        return json_response({'error': 'not permitted.'}, status=401)

    prev_task_details = Task(**task_collection).to_json()
    allowed_fields = ['name', 'short_description', 'details', 'tags']
    task_details = remove_extra_keys(request.get_json(), allowed_fields)

    # check if short description or details are missing
    task_details, empty_fields = remove_extra_spaces_in_dictionary(
        task_details, allowed_fields)

    duplicate_name_flag = False
    # check for duplicate task names
    if 'name' in task_details:
        existing_task = get_existing_task_details(
            db.mongo_db, task_details['name'].strip())
        if existing_task and existing_task['_id'] != task_object_id:
            duplicate_name_flag = True
            db.logger.warn(
                'error while updating : %s [ %s ] | %s task name already exists, skipping name field.' % (
                    prev_task_details['name'], task_object_id, task_details['name']))
            del task_details['name']

    # check invalid types for tags
    if 'tags' in task_details and not isinstance(task_details['tags'], list):
        return json_response(
            {'error': "`tag` field type didn't match. It must be list of strings."}, status=400)

    if len(empty_fields):
        db.logger.debug('%s empty fields identified while updating the task: %s [ _id: %s ]' % (
            empty_fields, prev_task_details['name'], task_object_id))

    changed_fields = []
    # check difference in new fields
    for key, value in prev_task_details.items():
        if key not in task_details:
            continue
        else:
            if key == 'tags' and len(
                    set(task_details['tags']).union(set(prev_task_details[key]))) == len(
                set(task_details['tags']).intersection(set(prev_task_details[key]))):
                continue
            elif task_details[key] == value:
                continue
            changed_fields.append(key)

    if len(changed_fields):
        task_details.update({'date_modified': datetime.utcnow()})
        task_details = jsonable_encoder(task_details, exclude_none=True)
        db.mongo_db.task.update_one({
            "_id": task_object_id,
        }, {
            "$set": task_details
        })

        db.logger.info('>> task updated %s [ %s ] | %s fields are changed' % (
            prev_task_details['name'], task_object_id, changed_fields))

    if duplicate_name_flag:
        return json_response({'response': 'Task name already exists.'})

    return json_response({'response': 'success'}, status=202)
