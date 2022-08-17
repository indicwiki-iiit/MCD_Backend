import pytest
from json import dumps, loads
from bson import json_util, ObjectId
from copy import deepcopy

from src import create_app
import src.database as db
from src.models import TASK_CRITICAL_FIELDS, USER_TYPES

from tests.utils import get_all_combs
from tests.Setup import Setup


# This is still left, not sure how file system works
class TestTaskCreationGeneric(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.app = create_app().test_client()
        self.generate_user(fake_user)
        self.task = fake_task()
        self.task['access_type'] = 'global-view'
        self.endpoint = {
            'path': f'/api/task/genric/?auth_token={self.auth_token}',
            'content_type': 'multipart/form-data'
        }

    def check_user_type(self):
        if self.user['user_type'] not in ['admin', 'problem_setter']:
            response = self.app.post(data=self.task, **self.endpoint)
            status, data = response.status_code, loads(response.data)
            assert status == 401
            assert 'error' in data
            return False
        return True

    def check_task_details(self, data):
        assert self.task['name'] == data['name']
        assert self.task['short_description'] == data['short_description']
        assert self.task['details'] == data['details']
        assert self.task['tags'] == data['tags']
        assert self.task['reward_levels'] == data['reward_levels']
        assert self.task['access_type'] == data['access_type']
        assert self.user['id'] == data['problem_setter_id']
        assert data['date_added'] == data['date_modified']

        std_langs = set()
        self.task['question_list'].sort(key=lambda x: x['question_prompt'])
        data['question_list'].sort(key=lambda x: x['question_prompt'])
        for (std_qn, res_qn) in zip(self.task['question_list'], data['question_list']):
            for key, val in std_qn.items():
                if isinstance(val, str):  val = val.strip()
                assert val == res_qn[key]
            std_langs.add(std_qn['language'])
        assert sorted(std_langs) == sorted(data['languages'])

    def test__critical_fields(self):
        critical_fields = deepcopy(TASK_CRITICAL_FIELDS)
        critical_fields.remove('problem_setter_id')
        critical_fields.remove('question_list')
        for fields in get_all_combs(critical_fields):
            body = deepcopy(self.task)
            for field in fields:
                body.pop(field)
            response = self.app.post(data=body, **self.endpoint)
            status, data = response.status_code, loads(response.data)
            assert status == 400
            assert 'error' in data
            assert sorted(data['missing_fields']) == sorted(fields)

    def test__empty_fields(self, fake_task):
        empty_fields = ['name', 'short_description', 'details']
        for fields in get_all_combs(empty_fields):
            body = deepcopy(self.task)
            for field in fields:
                body[field] = ''
            response = self.app.post(data=body, **self.endpoint)
            status, data = response.status_code, loads(response.data)
            assert status == 400
            assert 'error' in data
            assert sorted(data['empty_fields']) == sorted(fields)

    @pytest.mark.parametrize('user_type', USER_TYPES)
    def test__success(self, user_type):
        self.user['user_type'] = user_type
        user_id = ObjectId(self.user['id'])
        db.mongo_db.user.update_one({'_id': user_id}, {'$set': {'user_type': user_type}})
        if not self.check_user_type(): return
        response = self.app.post(data=self.task, **self.endpoint)
        # print(response.data)
        status, task_id = response.status_code, loads(response.data)['task']['id']
        db_entry = loads(json_util.dumps(db.mongo_db.task.find_one({'_id': ObjectId(task_id)})))
        assert status == 201
        self.check_task_details(db_entry)

    def test__same_task_name(self, fake_task):
        task_2 = fake_task()
        task_2['name'] = self.task['name']
        self.app.post(data=self.task, **self.endpoint)
        response = self.app.post(data=task_2, **self.endpoint)
        status, data = response.status_code, loads(response.data)
        assert status == 400
        assert 'error' in data
