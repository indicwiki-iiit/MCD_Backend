import random

import pytest
from json import dumps, loads
from bson import json_util, ObjectId
from copy import deepcopy

import src.database as db
from src.models import QUESTION_LEVELS, QUESTION_TYPES, TASK_TYPES

from tests.Setup import Setup


# Some checks are still left to get 100% for this API
class TestResponse(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.generate_user(fake_user)
        self.task = self.generate_task(fake_task)
        task_id = self.task['id']
        self.chosen_qn = random.choice(self.task['question_list'])
        self.endpoint = {
            'path': f"/api/task/{task_id}/annotation/{self.chosen_qn['id']}/?auth_token={self.auth_token}",
            'content_type': 'application/json',
        }

    def check_response_details(self, db_entry, posted_data):
        assert db_entry['response'] == posted_data['response']
        assert db_entry['response_type'] == posted_data['response_type']
        assert db_entry['task_id'] == self.task['id']
        assert db_entry['user_id'] == self.user['id']
        assert db_entry['question_id'] == self.chosen_qn['id']

    def test__incorrect_response_type(self, fake_response):
        user_response = fake_response()
        for qn_type in QUESTION_TYPES:
            if self.chosen_qn['question_type'] != qn_type:
                body = deepcopy(user_response)
                body['response_type'] = qn_type
                response = self.app.post(data=dumps(body), **self.endpoint)
                status, data = response.status_code, loads(response.data)
                assert status == 400
                assert 'error' in data

    @pytest.mark.parametrize('task_type', TASK_TYPES)
    def test__success(self, fake_response, task_type):
        task_id = ObjectId(self.task['id'])
        db.mongo_db.task.update_one({'_id': task_id}, {'$set': {'access_type': task_type}})
        body = fake_response()
        body['response_type'] = self.chosen_qn['question_type']
        response = self.app.post(data=dumps(body), **self.endpoint)
        status, annotation_id = response.status_code, loads(response.data)['annotation_id']

        db_entry = loads(
            json_util.dumps(db.mongo_db.response.find_one({'_id': ObjectId(annotation_id)})))
        user_new_score = loads(json_util.dumps(
            db.mongo_db.user.find_one({'_id': ObjectId(self.user['id'])})))['annotation_score']
        added_score = self.task['reward_levels'][
            QUESTION_LEVELS[self.chosen_qn.get('question_level', 'medium')]]

        assert status == 201
        self.check_response_details(db_entry, body)
        assert user_new_score - self.user['annotation_score'] == added_score

    @pytest.mark.parametrize('task_type', TASK_TYPES)
    def test__update_response(self, fake_response, task_type):
        task_id = ObjectId(self.task['id'])
        db.mongo_db.task.update_one({'_id': task_id}, {'$set': {'access_type': task_type}})
        body = fake_response()
        body['response_type'] = self.chosen_qn['question_type']
        body_2 = fake_response()
        body_2['response_type'] = self.chosen_qn['question_type']
        response = self.app.post(data=dumps(body), **self.endpoint)
        annotation_id = loads(response.data)['annotation_id']
        score_after_first = loads(json_util.dumps(
            db.mongo_db.user.find_one({'_id': ObjectId(self.user['id'])})))['annotation_score']

        response = self.app.post(data=dumps(body_2), **self.endpoint)
        status = response.status_code
        score_after_second = loads(json_util.dumps(
            db.mongo_db.user.find_one({'_id': ObjectId(self.user['id'])})))['annotation_score']

        db_entry = loads(
            json_util.dumps(db.mongo_db.response.find_one({'_id': ObjectId(annotation_id)})))
        assert status == 202
        self.check_response_details(db_entry, body_2)
        assert score_after_second - score_after_first == 0
