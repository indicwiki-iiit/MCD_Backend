from json import dumps, loads

from app import create_app
from src.models import USER_TYPES


class Setup:

    def set_app(self):
        self.app = create_app().test_client()

    def generate_user(self, fake_user, **kwargs):
        user = fake_user()
        if (u_type := kwargs.get('user_type', 'admin')) in USER_TYPES:
            user['user_type'] = u_type
        response = self.app.post('/user/', data=dumps(user), content_type='application/json')
        self.user = loads(response.data)['response']
        body = {'email': self.user['email']}
        response = self.app.post('/user/login/', data=dumps(body), content_type='application/json')
        self.auth_token = loads(response.data)['auth_token']

    def generate_task(self, fake_task, **kwargs):
        task = fake_task()
        if kwargs.get('task_type', None) is not None:
            task['access_type'] = kwargs['task_type']
        response = self.app.post(f'/task/genric/?auth_token={self.auth_token}', data=task,
                                 content_type='multipart/form-data')
        task = loads(response.data)['task']
        return task

    def insert_response(self, task_id, qn_id, body):
        response = self.app.post(
            f"/task/{task_id}/annotation/{qn_id}/?auth_token={self.auth_token}",
            data=dumps(body), content_type='application/json')
        return loads(response.data)
