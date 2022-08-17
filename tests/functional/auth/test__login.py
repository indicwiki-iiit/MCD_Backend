import pytest
from json import dumps, loads
from bson import json_util, ObjectId
import uuid

from src import create_app
import src.database as db


class TestLoginUser:

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user):
        self.app = create_app().test_client()
        self.user = fake_user()
        response = self.app.post('/api/user/', data=dumps(self.user), content_type='application/json')
        self.data = loads(response.data)['response']
        self.endpoint = {
            'path': '/api/user/login/',
            'content_type': 'application/json'
        }

    def test__empty_email(self):
        body = {'email': ''}
        response = self.app.post(data=dumps(body), **self.endpoint)
        status, data = response.status_code, loads(response.data)
        assert status == 400
        assert 'error' in data

    def test__no_user_found(self):
        body = {'email': 'abcd1234@xyz.com'}  # Random email
        response = self.app.post(data=dumps(body), **self.endpoint)
        status, data = response.status_code, loads(response.data)
        assert status == 404
        assert 'error' in data

    def test__login(self):
        body = {'email': self.user['email']}
        response = self.app.post(data=dumps(body), **self.endpoint)
        status, data = response.status_code, loads(response.data)
        assert status == 200
        try:
            uuid.UUID(data['auth_token'])
        except ValueError:
            assert False
        assert self.data['id'] == data['user_id']

    def test__same_auth_token(self):
        body = {'email': self.user['email']}
        user_id = ObjectId(self.data['id'])
        response = self.app.post(data=dumps(body), **self.endpoint)
        auth_token_1 = loads(response.data)['auth_token']
        response = self.app.post(data=dumps(body), **self.endpoint)
        auth_token_2 = loads(response.data)['auth_token']
        db_entry = loads(json_util.dumps(db.mongo_db.user.find_one({'_id': user_id})))
        assert auth_token_2 == auth_token_1
        assert auth_token_1 == db_entry['auth_token']
