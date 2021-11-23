import src.database as db
from .utils import get_number


def get_questions_for_exclusive_session(task_object_id, user_id, session_index=None,
                                        session_id=None):
    pipe = [{"$match": {"_id": task_object_id}},
            {"$unwind": "$question_list"},
            {"$match": {"question_list.assigned": user_id}},
            {"$group": {'_id': '$question_list.session_id',
                        "question_list": {"$push": "$question_list"}}}]
    # {"$sort" : {"_id": 1}}] )  ##commenting this aggregation as sort utilizes memory and might cause overflow on free tier servers
    cmd = db.mongo_db.task.aggregate(pipe)
    res = [x for x in cmd]
    # retrieve by session index
    if session_index is not None:
        final_res = sorted(res, key=lambda x: x['_id'])
        if session_index >= len(final_res):
            return []
        return final_res[session_index]['question_list']
    # retrieved by session_id
    if get_number(session_id) is not None:
        for session_data in res:
            if session_data['_id'] == get_number(session_id):
                return session_data['question_list']
    return []
