from collections import defaultdict

import src.database as db
from src.models.tasks import QUESTION_DISP_NAME


def get_question_count(task_id):
    """
        return number of question present in already exitsing task. This will throw an error on non-exitsing tasks
        args: task_id should be valid bson ObjectID
    """
    query = db.mongo_db.task.aggregate([
        {"$match": {'_id': task_id}}, {"$unwind": "$question_list"},
        {'$group': {'_id': "$question_list.question_type", "count": {"$sum": 1}}}
    ])
    resp = [x for x in query]
    # grouping the question_type
    question_collections = defaultdict(lambda: 0)
    for x in resp:
        question_collections[QUESTION_DISP_NAME.get(
            x['_id'], 'Unknown type')] = x['count']
    return question_collections
