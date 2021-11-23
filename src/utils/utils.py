import uuid
import csv
import json
from collections import OrderedDict
from datetime import datetime

from src.models.tasks import Question
from .languages import LANGUAGE_MAP, REVERSE_LANGUAGE_MAP

supported_languages = list(LANGUAGE_MAP.keys()) + \
                      [x.lower() for x in REVERSE_LANGUAGE_MAP.keys()]


def get_language_label(language_field, iso_code=True):
    if language_field in list(LANGUAGE_MAP.keys()):
        return language_field if iso_code else LANGUAGE_MAP[language_field]
    return language_field if not iso_code else REVERSE_LANGUAGE_MAP[language_field.capitalize()]


def processed_language_field(language_field, get_iso_code=True):
    language_support = True
    # checking whether valid language is present or not
    if language_field is None:
        language_field = 'en'
        return language_support, get_language_label(language_field, iso_code=get_iso_code)
    elif language_field.strip().lower() not in supported_languages:
        language_support = False
        return language_support, ""

    language_field = language_field.strip().lower()
    return language_support, get_language_label(language_field, iso_code=get_iso_code)


def filter_questions(question_list, logger):
    res = []
    count = 1
    for x in question_list:
        try:
            x.update({'id': str(uuid.uuid4()), 'seqno': count})
            # checking the question input language
            question_type = x['question_type']
            if question_type == 'text':
                textual_input_language = x.get('text_input_language', None)
                language_support_status, language_label = processed_language_field(
                    textual_input_language, get_iso_code=True)
                if not language_support_status:
                    continue
                x['text_input_language'] = language_label
            question_language = x.get('language', None)
            # checking the question prompt languages
            if question_language:
                language_support_status, language_label = processed_language_field(
                    question_language, get_iso_code=True)
                if not language_support_status:
                    continue
                x['language'] = language_label
            question_data = Question(**x)
            res.append(question_data)
            count += 1
        except Exception as e:
            logger.error(
                '[question] error encountered while processing question : %s. Error: %s' % (
                    x, str(e)))
    return res


def remove_extra_keys(src_dict: dict, essential_keys: list):
    return {k: v for k, v in src_dict.items() if k in essential_keys}


def remove_extra_spaces_in_dictionary(src_dict: dict, valid_keys: list = [],
                                      exclude_empty_fields=False):
    res = {}
    empty_fields = []
    for k, v in src_dict.items():
        if k in valid_keys:
            if not isinstance(v, str):
                res[k] = v
                continue
            temp = v.strip()
            if len(temp) == 0 or temp == '':
                empty_fields.append(k)
                if exclude_empty_fields:
                    continue
            res[k] = v.strip()
        else:
            res[k] = v
    return res, empty_fields


def get_existing_task_details(mongo_db, task_name):
    task_collection = mongo_db.task.find_one({'name': task_name.strip()})
    if task_collection:
        # instead of exact question return number of question present in the task
        task_collection['question_count'] = len(
            task_collection['question_list'])
        del task_collection['question_list']
        return task_collection
    return task_collection


def get_existing_user_details(mongo_db, user_email):
    user_collection = mongo_db.user.find_one({'email': user_email.strip()})
    return user_collection


def get_user_with_token(mongo_db, auth_token):
    user_row = mongo_db.user.find_one({"auth_token": auth_token.strip()})
    return user_row


def get_number(x):
    res = None
    if isinstance(x, int):
        return x
    try:
        res = int(str(x))
    except Exception:
        pass
    return res


def get_time_delta_str(last_recorded_time_str):
    last_recorded_time = datetime.strptime(' '.join(last_recorded_time_str.split('T')),
                                           '%Y-%m-%d %H:%M:%S.%f')
    delta = (datetime.utcnow() - last_recorded_time).total_seconds()

    time_quanta = OrderedDict()
    time_quanta['years'] = 60 * 60 * 24 * 365
    time_quanta['months'] = 60 * 60 * 24 * 30
    time_quanta['days'] = 60 * 60 * 24
    time_quanta['hours'] = 60 * 60
    time_quanta['minutes'] = 60
    time_quanta['seconds'] = 1

    time_label = ''
    for time_str, value in time_quanta.items():
        if delta > value:
            literal_value = int(delta / value)
            time_label = "%d %s" % (literal_value, time_str if literal_value > 1 else time_str[:-1])
            break

    return time_label


def get_proper_date_str(time_str):
    recorded_time = datetime.strptime(' '.join(time_str.split('T')), '%Y-%m-%d %H:%M:%S.%f')
    return recorded_time.strftime("%d %b %Y")


class FileReader:
    def __init__(self, filepath):
        self.filepath = filepath

    def load_data(self):
        res = self.load_json()
        if len(res):
            return res
        res = self.load_jsonl()
        if len(res):
            return res
        res = self.load_csv()
        if len(res):
            return res

    def load_jsonl(self):
        res = []
        try:
            with open(self.filepath, encoding='utf-8') as dfile:
                for line in dfile.readlines():
                    temp_json = json.loads(line.strip())
                    res.append(temp_json)
            return res
        except Exception as e:
            return res

    def load_json(self):
        res = []
        try:
            with open(self.filepath, encoding='utf-8') as dfile:
                temp_json = json.load(dfile)
                if not isinstance(temp_json, list):
                    return []
                return temp_json
        except Exception as e:
            return res

    def load_csv(self):
        res = []
        try:
            with open(self.filepath, encoding='utf-8') as dfile:
                line_count = 0
                csv_reader = csv.DictReader(dfile)
                for row in csv_reader:
                    if line_count == 0:
                        line_count += 1
                        continue
                    res.append(row)
                    line_count += 1
            return res
        except Exception as e:
            return res
