import uuid
from datetime import datetime

from flask import Blueprint, request

import src.database as db
from src.models import User, USER_CRITICAL_FIELDS, ALL_USER_FIELDS, USER_TYPES
from src.utils import json_response, remove_extra_keys, get_existing_user_details

general_auth_api = Blueprint('general_auth_api', __name__)


@general_auth_api.route('/user/', methods=['POST'])
def create_user():
    user_details = request.get_json()
    # check the missing fields
    missing_fields = set(USER_CRITICAL_FIELDS).difference(
        set(user_details.keys()))
    db.logger.debug(missing_fields)
    if len(missing_fields):
        return json_response({'error': 'some critical fields are missing.',
                              'missing_fields': list(missing_fields)}, status=400)

    user_details = remove_extra_keys(user_details, ALL_USER_FIELDS)

    # check if short description or details are missing
    empty_fields = []
    for field in USER_CRITICAL_FIELDS:
        processed_values = user_details[field].strip()
        if len(processed_values) == 0 or processed_values == '':
            empty_fields.append(field)

    if len(empty_fields):
        return json_response({"error": "important fields are empty.", "empty_fields": empty_fields},
                             status=400)

    # check invalid input for user_type
    if user_details.get('user_type', None) and user_details['user_type'].strip() not in USER_TYPES:
        return json_response({'error': "user_type is invalid."}, status=400)

    # check for existing user with email
    exitsing_user = get_existing_user_details(
        db.mongo_db, user_details['email'].strip())
    if exitsing_user:
        return json_response({'error': "user exists with same email address",
                              "error_type": "duplicate_email"}, status=400)

    user_details.update({
        'last_active': datetime.utcnow(),
        'date_joined': datetime.utcnow(),
    })

    user_row = User(**user_details)
    new_user = db.mongo_db.user.insert_one(user_row.to_json())
    db.logger.info('new user added user_id : %s | %s' % (new_user.inserted_id, user_row))
    user_obj = user_row.to_json()
    user_obj['id'] = str(new_user.inserted_id)
    return json_response({'response': user_obj}, status=201)


@general_auth_api.route('/user/login/', methods=['POST'])
def user_login():
    user_data = request.get_json()
    user_email = user_data.get('email', None)

    if not user_email:
        return json_response({'error': "email or password is missing."}, status=400)

    user_email = user_email.strip()
    user_row = db.mongo_db.user.find_one({'email': user_email})

    if not user_row:
        return json_response({'error': "user not found"}, status=404)

    new_info = {'last_active': str(datetime.utcnow())}
    if user_row['auth_token'].strip() == "UNASSIGNED":
        db.logger.info('[ new register ] obtaining auth token')
        auth_token = str(uuid.uuid4())
        new_info.update({'auth_token': auth_token})
    else:
        db.logger.info('[ old user ] %s logging in' % (user_email))
        auth_token = user_row['auth_token']

    db.mongo_db.user.update_one({'email': user_email}, {"$set": new_info})

    display_username = user_row['first_name'].capitalize() + " " + \
                       user_row['last_name'].capitalize()[0] + '.'
    return json_response({'response': 'success', 'user_name': display_username,
                          'auth_token': auth_token, 'user_type': user_row['user_type'],
                          'user_id': str(user_row['_id'])})
