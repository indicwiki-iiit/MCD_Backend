import random

import pytest
from json import  loads
from bson import json_util, ObjectId

import src.database as db
from tests.Setup import Setup


@pytest.mark.skip(reason="Probably Some issue in mongomock, doesn't handle update_many properly")
class TestRequestQuestions(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.generate_user(fake_user)
        self.task = self.generate_task(fake_task, task_type='single-view')
        task_id = self.task['id']
        self.chosen_qn = random.choice(self.task['question_list'])
        self.session_length = random.randint(1, len(self.task['question_list']))
        self.endpoint = {
            'path': f"/api/task/{task_id}/request_questions/?auth_token={self.auth_token}&session_length={self.session_length}",
            'content_type': 'application/json',
        }

    def check_unchanged_qn_fields(self, db_entry):
        prev_data = self.task['question_list']
        checking_fields = ['id', 'question_prompt', 'question_type', 'review_flag', 'language',
                           'question_contexts', 'response_options', 'text_input_language',
                           'question_level']
        for field in checking_fields:
            assert db_entry.get(field, '') == prev_data.get(field, '')

    def test__success(self, fake_task):
        task_id = ObjectId(self.task['id'])
        response = db.mongo_db.task.aggregate([
            {'$match': {'_id': task_id}},
            {'$project': {'max_session_id': {'$max': '$question_list.session_id'}}}
        ])
        prev_max_session_id = loads(json_util.dumps(response))[0]['max_session_id']
        response = self.app.post(**self.endpoint)
        print(response.data)
        status, questions = response.status_code, loads(response.data)['questions']
        changed_qn_ids = set([x['id'] for x in questions])
        self.task['question_list'].sort(key=lambda x: x['id'])
        response = loads(json_util.dumps(db.mongo_db.task.find({'_id': task_id})))
        new_questions = sorted(response['questions'], key=lambda x: x['id'])

        assert status == 200
        for qn in new_questions:
            self.check_unchanged_qn_fields(qn)
            if qn['id'] in changed_qn_ids:
                assert self.task['question_list']['session_id'] == prev_max_session_id + 1
                assert self.task['question_list']['assigned'] == self.user['id']
            else:
                assert self.task['question_list']['session_id'] == qn['session_id']
                assert self.task['question_list']['assigned'] == qn['assigned']
