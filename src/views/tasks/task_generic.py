import os
import json
from datetime import datetime

from flask import Blueprint, request

import src.database as db
from config import Config
from src.models import Task, ALL_TASK_FIELDS, DEFAULT_MAX_QUESTIONS, DEFAULT_MIN_QUESTIONS
from src.utils import json_response, remove_extra_keys, get_existing_task_details, filter_questions, \
    get_user_with_token, FileReader, get_number

task_generic_api = Blueprint('task_generic_api', __name__)


@task_generic_api.route("/genric/", methods=["POST"])
def create_generic_task():
    creator_details = get_user_with_token(
        db.mongo_db, request.args.get('auth_token', ''))
    if not creator_details or creator_details['user_type'] not in ['problem_setter', 'admin']:
        return json_response({'error': 'not permitted.'}, status=401)

    raw_task_details = request.form.to_dict(flat=False)
    allowed_list_keys = ['tags', 'reward_levels']
    task_details = {}
    for key, val in raw_task_details.items():
        if key in allowed_list_keys:
            task_details[key] = val
            continue
        task_details[key] = val[0]
    # task_details = request.get_json()
    # updating the problem setter id
    task_details['problem_setter_id'] = str(creator_details['_id'])
    # check the missing fields
    valuable_fields = ['name', 'short_description',
                       'details', 'problem_setter_id', 'tags']
    missing_fields = set(valuable_fields).difference(
        set(task_details.keys()))
    if len(missing_fields):
        return json_response(
            {'error': 'Some critical fields are missing: %s.' % ', '.join(list(missing_fields)),
             'missing_fields': list(missing_fields)}, status=400)

    task_details = remove_extra_keys(task_details, ALL_TASK_FIELDS)

    # check if short description or details are missing
    empty_fields = []
    for field in ['name', 'short_description', 'details']:
        processed_values = task_details[field].strip()
        if len(processed_values) == 0 or processed_values == '':
            empty_fields.append(field)

    if len(empty_fields):
        return json_response(
            {"error": "Important fields are missing: %s." % ', '.join(list(empty_fields)),
             "empty_fields": empty_fields}, status=400)

    # check invalid types
    is_valid_fields = True
    for field in ['tags', 'reward_levels']:
        if field not in task_details:
            continue
        if not isinstance(task_details[field], list):
            is_valid_fields = False

    if not is_valid_fields:
        return json_response({'error': "field type didn't match."}, status=400)

    # check for existing task with same name
    exitsing_task = get_existing_task_details(
        db.mongo_db, task_details['name'].strip())
    if exitsing_task:
        return json_response({'error': "task name already exists.", "error_type": "duplicate_task"},
                             status=400)

    # checking min and max questions if type is single view
    if task_details.get('access_type', '') == 'single-view':
        min_question_count = get_number(
            task_details.get('min_question_count', DEFAULT_MIN_QUESTIONS))
        max_question_count = get_number(
            task_details.get('max_question_count', DEFAULT_MAX_QUESTIONS))

        # min and max are not numbers
        if min_question_count is None or max_question_count is None:
            return json_response({
                'error': "invalid number specified for minimum or maximum question count per session.",
                "error_type": "invalid_input"}, status=400)

        # checking for edge cases
        if min_question_count == 0 or max_question_count == 0:
            return json_response(
                {'error': "min or max question count per session should not be zero.",
                 "error_type": "invalid_input"}, status=400)

        if min_question_count > max_question_count:
            return json_response({
                'error': "min number of question can't be greater than max number of questions per session.",
                "error_type": "invalid_input"}, status=400)

    # reading the uploaded files
    uploaded_file = request.files.get('file', None)
    if uploaded_file is not None and uploaded_file.filename != '':
        if Config.DB_DEPLOYMENT == 'production':
            target_dir = os.path.join(
                '/', 'tmp', 'uploaded_docs', "%s-%s" % (creator_details["_id"], datetime.utcnow()))
        else:
            target_dir = os.path.join(
                './', 'uploaded_docs', "%s-%s" % (creator_details["_id"], datetime.utcnow()))
        db.logger.info("storing the question file to directory : %s" % target_dir)
        os.makedirs(target_dir, exist_ok=True)
        destination_path = os.path.join(target_dir, uploaded_file.filename)
        uploaded_file.save(destination_path)
    else:
        db.logger.info("Files are not uploaded properly")
        return json_response({'error': 'Format of file is incorrect.'}, status=400)

    jsonl_reader = FileReader(destination_path)
    question_list = jsonl_reader.load_data()

    try:
        os.remove(destination_path)
        db.logger.info("%s file removed successfully." % destination_path)
        os.rmdir(target_dir)
        db.logger.info("%s folder removed successfully." % target_dir)
    except Exception as e:
        db.logger.error(
            "error encountered while removing folder: %s. Error: %s" % (target_dir, str(e)))

    # check for empty question_list
    if not question_list or len(question_list) == 0:
        return json_response({'error': "question_list should contain atleast one question"},
                             status=400)

    filtered_questions = filter_questions(question_list, db.logger)
    invalid_questions = len(question_list) - len(filtered_questions)
    languages = set([x.language for x in filtered_questions])

    db.logger.info(
        '[%s] task created by problem_setter: %s with task_name : %s contains %d invalid questions, out of %d total questions across %d languages' % (
            task_details['access_type'], task_details['problem_setter_id'], task_details['name'],
            invalid_questions, len(question_list), len(languages)))
    db.logger.info('question langauges are : %s' % languages)

    if len(filtered_questions) == 0:
        return json_response({'error': "question_list should contain atleast one valid question",
                              'invalid_question_count': invalid_questions}, status=400)

    # checking min and max questions are logically sound wrt valid question count
    if task_details.get('access_type', '') == 'single-view' and len(
            filtered_questions) < min_question_count:
        return json_response({
            'error': 'mininum number of question per session is greater than total number of questions.'},
            status=400)

    date_created = datetime.utcnow()    
    task_details.update({'date_added': date_created,
                         'date_modified': date_created,
                         'languages': languages,
                         'question_list': filtered_questions})

    if task_details.get('access_type', '') == 'single-view':
        task_details.update(
            {'max_question_count': max_question_count, 'min_question_count': min_question_count})

    task_collection = Task(**task_details)
    new_task = db.mongo_db.task.insert_one(task_collection.to_json())
    task_ob = task_collection.to_json()
    task_ob['id'] = str(new_task.inserted_id)
    db.logger.info('successfully stored the question.')

    return json_response({'status': 'success', 'valid_question_count': len(filtered_questions),
                          'invalid_question_count': invalid_questions, 'task': task_ob}, status=201)
