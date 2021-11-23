import json
from bson import json_util

import src.database as db


# This returns an aggregate query for getting no. of assigned or unassigned
# questions depending on the parameter
def get_question_assignment_count_query(isEqual: bool):
    # If True then gives query for counting assigned questions else unassigned
    cond = "$eq" if not isEqual else "$ne"  # Which condition to use
    return {  # Query return the size of filtered array based on the condition given
        "$size": {
            "$filter": {
                "input": "$question_list",
                "as": "ql",
                "cond": {cond: ["$$ql.assigned", ""]}
            }
        }
    }


# This function returns the aggregate query to get all responses for each question
# obtained by matching documents from the task_filter
def get_questions_with_responses_from_task_query(task_filter):
    """
    Changed the implementation to have it in testing, since
    let + pipeline in lookup aggregation pipeline is not supported in mongomock
    """
    # return [
    #     {"$match": task_filter},  # get the task
    #     {"$unwind": "$question_list"},
    #     {"$lookup": {  # add responses for each question in the task
    #         "from": "response",
    #         "let": {"qid": "$question_list.id"},
    #         "pipeline": [
    #             {"$match": {"$expr": {"$eq": ["$question_id", "$$qid"]}}},
    #             {"$project": {"response": 1, "_id": 1, "user_id": 1}}
    #         ],
    #         "as": "responses",
    #     }},
    # ]
    return [
        {"$match": task_filter},  # get the task
        {"$unwind": "$question_list"},
        {"$lookup": {  # add responses for each question in the task
            "from": "response",
            "localField": "question_list.id",
            "foreignField": "question_id",
            "as": "responses",
        }},
    ]


# This function returns the number of annotated questions based on the filter passed
def get_annotated_question_count(task_filter):
    pipeline = get_questions_with_responses_from_task_query(task_filter) + [
        {"$addFields": {"response_count": {"$size": "$responses"}}},
        {"$match": {"response_count": {"$gt": 0}}},
        {"$count": "annotated_count"},
    ]
    res = db.mongo_db.task.aggregate(pipeline)
    res = json.loads(json_util.dumps(res, indent=2))
    if len(res) == 0:
        return 0
    return res[0]["annotated_count"]


# This function returns the whole count_details object to get question counts based
# on the provided filter. If the task is not single view, this return empty dictionary
def question_counts(task_filter):
    res = db.mongo_db.task.aggregate([
        {"$match": task_filter},
        {"$match": {"access_type": "single-view"}},
        {"$project": {
            "assigned": get_question_assignment_count_query(True),
            "unassigned": get_question_assignment_count_query(False),
        }}
    ])
    res = json.loads(json_util.dumps(res, indent=2))
    if not res:
        return {}
    res = res[0]
    res["annotated"] = get_annotated_question_count(task_filter)
    del res["_id"]
    return res
