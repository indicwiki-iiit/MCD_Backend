import pytest
from json import dumps, loads
from bson import json_util, ObjectId

import src.database as db
from tests.Setup import Setup


# Some checks are still left to get 100% for this API
class TestTaskUpdate(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.generate_user(fake_user)
        self.task = self.generate_task(fake_task)
        task_id = self.task['id']
        self.endpoint = {
            'path': f"/task/{task_id}/?auth_token={self.auth_token}",
            'content_type': 'application/json',
        }

    def check_task_details(self, db_entry, posted_data):
        assert db_entry['name'] == posted_data['name']
        assert db_entry['tags'] == posted_data['tags']
        assert db_entry['short_description'] == posted_data['short_description']
        assert db_entry['details'] == posted_data['details']
        assert db_entry['access_type'] == self.task['access_type']
        assert db_entry['question_list'] == self.task['question_list']
        assert db_entry['reward_levels'] == self.task['reward_levels']
        assert db_entry['date_modified'] != self.task['date_modified']

    def test__success(self, fake_task):
        body = fake_task()
        body.pop('file', None)
        response = self.app.put(data=dumps(body), **self.endpoint)
        status = response.status_code
        task_id = self.task['id']
        db_entry = loads(json_util.dumps(db.mongo_db.task.find_one({'_id': ObjectId(task_id)})))
        assert status == 202
        self.check_task_details(db_entry, body)

    # def test_update_response(self, fake_response):
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
