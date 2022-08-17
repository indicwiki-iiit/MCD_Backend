import pytest
from json import loads
from collections import Counter
from bson import ObjectId

import src.database as db
from src.utils import LANGUAGE_MAP
from src.models import TASK_TYPES
from tests.Setup import Setup
from tests.utils import QUESTION_MAP


class TestTask(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.generate_user(fake_user)
        self.task = self.generate_task(fake_task)

        self.endpoint = {
            'path': f"/api/task/{self.task['id']}/?auth_token={self.auth_token}"
        }

    def modify_task(self, task_type):
        self.task['access_type'] = task_type
        self.task['_id'] = self.task.pop('id', '')
        qns = self.task.pop('question_list', [])
        self.task['languages'] = [LANGUAGE_MAP[x] for x in self.task['languages']]
        self.task['question_count'] = dict(Counter([QUESTION_MAP[x['question_type']] for x in qns]))
        self.task['single_view_stats'] = {}
        if task_type == 'single-view':
            self.task['single_view_stats'] = {'assigned': 0, 'annotated': 0, 'unassigned': len(qns)}

    @pytest.mark.xfail(reason='Date formatted in backend, should be done in frontend')
    @pytest.mark.parametrize('task_type', TASK_TYPES)
    def test__get_task(self, task_type):
        task_id = ObjectId(self.task['id'])
        db.mongo_db.task.update_one({'_id': task_id}, {"$set": {'access_type': task_type}})
        self.modify_task(task_type)

        response = self.app.get(**self.endpoint)
        status, data = response.status_code, loads(response.data)['response']

        assert status == 200
        assert data == self.task
