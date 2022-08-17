import random

import pytest
from json import dumps, loads
from bson import json_util, ObjectId

from src import create_app
import src.database as db
from tests.Setup import Setup


# Some checks are still left to get 100% for this API
class TestTaskUpdate(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.generate_user(fake_user, user_type='any')
        self.endpoint = {
            'path': f"/api/user/{self.user['id']}/?auth_token={self.auth_token}",
            'content_type': 'application/json'
        }

    def check_task_details(self, db_entry, posted_data):
        assert db_entry['first_name'] == posted_data['first_name']
        assert db_entry['last_name'] == posted_data['last_name']
        assert db_entry['description'] == posted_data['description']
        assert db_entry['email'] == self.user['email']
        assert db_entry['user_type'] == self.user['user_type']
        assert db_entry['annotation_score'] == self.user['annotation_score']
        assert db_entry['date_joined'] == self.user['date_joined']
        assert db_entry['last_active'] != self.user['last_active']

    def test__success(self, fake_user):
        body = fake_user()
        response = self.app.put(data=dumps(body), **self.endpoint)
        status = response.status_code
        user_id = self.user['id']
        db_entry = loads(json_util.dumps(db.mongo_db.user.find_one({'_id': ObjectId(user_id)})))
        assert status == 202
        self.check_task_details(db_entry, body)

    # def test__update_response(self, fake_response):
    #     body = fake_response()
    #     body['response_type'] = self.chosen_qn['question_type']
    #     body_2 = fake_response()
    #     body_2['response_type'] = self.chosen_qn['question_type']
    #     response = self.app.post(data=dumps(body), **self.endpoint)
    #     annotation_id = loads(response.data)['annotation_id']
    #     score_after_first = loads(json_util.dumps(
    #         db.mongo_db.user.find_one({'_id': ObjectId(self.user['id'])})))['annotation_score']
    #
    #     response = self.app.post(data=dumps(body_2), **self.endpoint)
    #     status = response.status_code
    #     score_after_second = loads(json_util.dumps(
    #         db.mongo_db.user.find_one({'_id': ObjectId(self.user['id'])})))['annotation_score']
    #
    #     db_entry = loads(
    #         json_util.dumps(db.mongo_db.response.find_one({'_id': ObjectId(annotation_id)})))
    #     assert status == 202
    #     self.check_response_details(db_entry, body)
    #     assert score_after_second - score_after_first == 0
