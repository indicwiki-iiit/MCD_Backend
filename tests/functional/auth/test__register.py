import pytest
from json import dumps, loads
from copy import deepcopy
from bson import json_util, ObjectId

from src import create_app
from tests.utils import get_all_combs
from src.models import USER_CRITICAL_FIELDS
import src.database as db


class TestRegisterUser:

    @pytest.fixture(autouse=True)
    def setUp(self, init_db):
        self.app = create_app().test_client()
        self.endpoint = {
            'path': '/api/user/',
            'content_type': 'application/json',
        }

    @staticmethod
    def check_user_details(user, data):
        assert user['first_name'] == data['first_name']
        assert user['last_name'] == data['last_name']
        assert user['email'] == data['email']
        assert user['description'] == data['description']
        assert user['user_type'] == data['user_type']

    def test__critical_fields(self, fake_user):
        user = fake_user()
        for fields in get_all_combs(USER_CRITICAL_FIELDS):
            body = deepcopy(user)
            for field in fields:
                body.pop(field)
            response = self.app.post(data=dumps(body), **self.endpoint)
            status, data = response.status_code, loads(response.data)
            assert status == 400
            assert 'error' in data
            assert sorted(data['missing_fields']) == sorted(fields)

    def test__empty_fields(self, fake_user):
        user = fake_user()
        for fields in get_all_combs(USER_CRITICAL_FIELDS):
            body = deepcopy(user)
            for field in fields:
                body[field] = ''
            response = self.app.post(data=dumps(body), **self.endpoint)
            status, data = response.status_code, loads(response.data)
            assert status == 400
            assert 'error' in data
            assert sorted(data['empty_fields']) == sorted(fields)

    def test__bad_user_type(self, fake_user):
        user = fake_user()
        user['user_type'] = 'abcd'  # Random user_type
        response = self.app.post(data=dumps(user), **self.endpoint)
        status, data = response.status_code, loads(response.data)
        assert status == 400
        assert 'error' in data

    def test__success(self, fake_user):
        user = fake_user()
        response = self.app.post(data=dumps(user), **self.endpoint)
        status, user_id = response.status_code, loads(response.data)['response']['id']
        db_entry = loads(json_util.dumps(db.mongo_db.user.find_one({'_id': ObjectId(user_id)})))
        assert status == 201
        self.check_user_details(user, db_entry)
        assert 'UNASSIGNED' == db_entry['auth_token']

    def test__same_email(self, fake_user):
        user_1 = fake_user()
        user_2 = fake_user()
        user_2['email'] = user_1['email']
        self.app.post(data=dumps(user_1), **self.endpoint)
        response_2 = self.app.post(data=dumps(user_2), **self.endpoint)
        assert response_2.status_code == 400
        assert 'error' in loads(response_2.data)
        assert loads(response_2.data).get('error_type', None) == 'duplicate_email'
