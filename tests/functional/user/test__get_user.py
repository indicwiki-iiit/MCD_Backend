from json import loads

import pytest

from tests.Setup import Setup


class TestUser(Setup):

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.users = []
        for i in range(5):
            self.generate_user(fake_user, user_type='problem_setter')
            self.user.pop('last_active', '')
            self.users.append(self.user)
        self.users.sort(key=lambda x: x['email'])

    def test__get_all_users(self):

        response = self.app.get(f"/user/")
        status, data = response.status_code, loads(response.data)['response']
        data.sort(key=lambda x: x['email'])

        for i in range(len(self.users)):
            self.users[i]['_id'] = self.users[i].pop('id', '')
            self.users[i].pop('auth_token', '')
            data[i].pop('last_active', '')

        assert status == 200
        assert data == self.users
