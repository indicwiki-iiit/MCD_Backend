import random
from copy import deepcopy
from json import loads

import pytest
from bson import ObjectId

import src.database as db
from tests.Setup import Setup


class TestSingleViewStats(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task, fake_response):
        self.set_app()
        self.generate_user(fake_user)
        self.task = self.generate_task(fake_task, task_type='single-view')
        task_id = self.task['id']
        qns = len(self.task['question_list'])

        self.result = {
            'annotated': 0,
            'assigned': 0,
            'unassigned': qns
        }

        modified_qns = deepcopy(self.task['question_list'])
        for x in range(qns):
            if random.random() > .5:
                modified_qns[x].update({'session_id': x, 'assigned': self.user['id']})
                self.result['assigned'] += 1
                self.result['unassigned'] -= 1
                if random.random() > 0.5:
                    body = fake_response()
                    body['response_type'] = modified_qns[x]['question_type']
                    self.insert_response(task_id, modified_qns[x]['id'], body)
                    self.result['annotated'] += 1

        db.mongo_db.task.update_one({"_id": ObjectId(task_id)},
                                    {'$set': {'question_list': modified_qns}})
        self.endpoint = {
            'path': f"/task/{task_id}/single_view_stats/",
            'content_type': 'application/json',
        }

    def test__success(self, fake_task):
        response = self.app.get(**self.endpoint)
        status, stats = response.status_code, loads(response.data)
        assert status == 200
        assert self.result == stats
