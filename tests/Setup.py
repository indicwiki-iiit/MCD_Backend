from app import create_app
from json import dumps, loads


class Setup:

    def set_app(self):
        self.app = create_app().test_client()

    def generate_user(self, fake_user, **kwargs):
        user = fake_user()
        if kwargs.get('user_type', 'admin') == 'admin':
            user['user_type'] = 'admin'
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
