from flask import Blueprint, request

import src.database as db
from src.utils import json_response, get_user_with_token, get_number, get_time_delta_str

leaderboard_api = Blueprint('leaderboard_api', __name__)


@leaderboard_api.route('/leaderboard/', methods=['GET'])
def get_leaderboard():
    user_email = ''
    if request.args.get('auth_token', None):
        end_user = get_user_with_token(db.mongo_db, request.args.get('auth_token', ''))
        if end_user:
            user_email = end_user['email'].strip()

    threshold = request.args.get('threshold', None)
    threshold = get_number(threshold)
    if threshold is None:
        threshold = 10
    all_user_details = db.mongo_db.user.find({})
    rank_list = []
    for x in all_user_details:
        # rank_list.append([x['first_name'], x['last_name'], x['email'].strip(), x['review_score'] +
        #                  x['annotation_score']+x['milestone_score'], str(x['last_active'])])
        rank_list.append({
            'first_name': x['first_name'],
            'last_name': x['last_name'],
            'email': x['email'],
            'final_score': x['review_score'] + x['annotation_score'] + x['milestone_score'],
            'last_active': "%s ago" % get_time_delta_str(str(x['last_active'])),
            'user_id': str(x["_id"])
        })

    final_rank_list = []
    user_rank_list = []
    for i, x in enumerate(sorted(rank_list, key=lambda x: x['final_score'], reverse=True)):
        x.update({'rank': i + 1})
        # final_rank_list.append([i+1] + x)
        final_rank_list.append(x)
        if len(user_email) > 0 and x['email'] == user_email and i + 1 > threshold:
            x.update({'rank': i + 1})
            user_rank_list.append(x)

    return json_response({'response': final_rank_list[:threshold], 'user_rank': user_rank_list})
