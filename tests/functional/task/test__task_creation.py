# import pytest
# from json import dumps, loads
# from bson import json_util, ObjectId
# from copy import deepcopy
#
# from src import create_app
# import src.database as db
# from src.models import TASK_CRITICAL_FIELDS, USER_TYPES
#
# from tests.utils import get_all_combs
#
#
# # Some checks are still left to get 100% for this API
# @pytest.mark.xfail(reason="This API is not used now")
# class TestTaskCreation:
#
#     @pytest.fixture(autouse=True)
#     def setUp(self, init_db, fake_user, fake_task):
#         self.app = create_app().test_client()
#         self.user = fake_user()
#         self.user['user_type'] = 'admin'
#         response = self.app.post('/user/', data=dumps(self.user), content_type='application/json')
#         self.user_id = loads(response.data)['response']['id']
#         body = {'email': self.user['email']}
#         response = self.app.post('/user/login/', data=dumps(body), content_type='application/json')
#         auth_token = loads(response.data)['auth_token']
#         self.task = fake_task()
#         self.endpoint = {
#             'path': f'/task/?auth_token={auth_token}',
#             'content_type': 'application/json',
#         }
#
#     def check_user_type(self):
#         print(self.user['user_type'])
#         if self.user['user_type'] not in ['admin', 'problem_setter']:
#             response = self.app.post(data=dumps(self.task), **self.endpoint)
#             status, data = response.status_code, loads(response.data)
#             assert status == 401
#             assert 'error' in data
#             return False
#         return True
#
#     def check_task_details(self, data):
#         assert self.task['name'] == data['name']
#         assert self.task['short_description'] == data['short_description']
#         assert self.task['details'] == data['details']
#         assert self.task['tags'] == data['tags']
#         assert self.task['reward_levels'] == data['reward_levels']
#         assert self.task['access_type'] == data['access_type']
#         assert self.user_id == data['problem_setter_id']
#
#         std_langs = set()
#         self.task['question_list'].sort(key=lambda x: x['question_prompt'])
#         data['question_list'].sort(key=lambda x: x['question_prompt'])
#         for (std_qn, res_qn) in zip(self.task['question_list'], data['question_list']):
#             for key, val in std_qn.items():
#                 if isinstance(val, str):  val = val.strip()
#                 assert val == res_qn[key]
#             std_langs.add(std_qn['language'])
#         assert sorted(std_langs) == sorted(data['languages'])
#
#     def test__critical_fields(self):
#         critical_fields = deepcopy(TASK_CRITICAL_FIELDS)
#         critical_fields.remove('problem_setter_id')
#         for fields in get_all_combs(critical_fields):
#             body = deepcopy(self.task)
#             for field in fields:
#                 body.pop(field)
#             response = self.app.post(data=dumps(body), **self.endpoint)
#             status, data = response.status_code, loads(response.data)
#             assert status == 400
#             assert 'error' in data
#             assert sorted(data['missing_fields']) == sorted(fields)
#
#     def test__empty_fields(self, fake_task):
#         empty_fields = ['name', 'short_description', 'details']
#         for fields in get_all_combs(empty_fields):
#             body = deepcopy(self.task)
#             for field in fields:
#                 body[field] = ''
#             response = self.app.post(data=dumps(body), **self.endpoint)
#             status, data = response.status_code, loads(response.data)
#             assert status == 400
#             assert 'error' in data
#             assert sorted(data['empty_fields']) == sorted(fields)
#
#     def test__empty_question_list(self):
#         self.task['question_list'] = []
#         response = self.app.post(data=dumps(self.task), **self.endpoint)
#         status, data = response.status_code, loads(response.data)
#         assert status == 400
#         assert 'error' in data
#
#     @pytest.mark.parametrize('user_type', USER_TYPES)
#     def test__success(self, user_type):
#         db.mongo_db.user.update_one({'_id': self.user_id}, {'$set': {'user_type': user_type}})
#         if not self.check_user_type(): return
#         response = self.app.post(data=dumps(self.task), **self.endpoint)
#         status, task_id = response.status_code, loads(response.data)['task']['id']
#         db_entry = loads(json_util.dumps(db.mongo_db.task.find_one({'_id': ObjectId(task_id)})))
#         assert status == 201
#         self.check_task_details(db_entry)
#
#     def test__same_task_name(self, fake_task):
#         task_2 = fake_task()
#         task_2['name'] = self.task['name']
#         self.app.post(data=dumps(self.task), **self.endpoint)
#         response = self.app.post(data=dumps(task_2), **self.endpoint)
#         status, data = response.status_code, loads(response.data)
#         assert status == 400
#         assert 'error' in data
