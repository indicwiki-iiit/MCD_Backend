import json

from .get_assigned_question_count import question_counts, get_question_assignment_count_query, \
    get_annotated_question_count, get_questions_with_responses_from_task_query
from .get_question_count import get_question_count
from .utils import get_language_label, processed_language_field, filter_questions, \
    remove_extra_keys, remove_extra_spaces_in_dictionary, get_existing_task_details, \
    get_existing_user_details, get_user_with_token, get_number, get_time_delta_str, \
    get_proper_date_str, FileReader
from .languages import REVERSE_LANGUAGE_MAP, LANGUAGE_MAP
from .get_questions_for_exclusive_session import get_questions_for_exclusive_session


def json_response(payload, status=200):
    return json.dumps(payload), status, {'content-type': 'application/json'}
