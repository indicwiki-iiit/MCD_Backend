from json import loads

import dateutil.parser
import pytest
from bson import ObjectId

import src.database as db
from tests.Setup import Setup


class TestTaskReport(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.tasks = []
        for i in range(5):
            self.generate_user(fake_user, user_type='problem_setter')
            task = self.generate_task(fake_task)
            self.tasks.append(task)
        self.tasks.sort(key=lambda x: dateutil.parser.isoparse(x['date_added']))

    @pytest.mark.parametrize('user_type', ['admin', 'problem_setter'])
    def test__get_creator_task(self, user_type):
        self.user['user_type'] = user_type
        user_id = ObjectId(self.user['id'])
        db.mongo_db.user.update_one({'_id': user_id}, {'$set': {'user_type': user_type}})

        response = self.app.get(f"/task/creator/?auth_token={self.auth_token}")
        status, data = response.status_code, loads(response.data)['response']
        data.sort(key=lambda x: dateutil.parser.isoparse(x['date_added']))

        if user_type == 'problem_setter':
            self.tasks = self.tasks[-1:]

        for i in range(len(self.tasks)):
            self.tasks[i]['_id'] = self.tasks[i].pop('id', '')
            self.tasks[i].pop('question_list', [])
            self.tasks[i].pop('details')

        assert status == 200
        assert data == self.tasks
