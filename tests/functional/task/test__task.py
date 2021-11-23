import random
import string
import pytest
from json import loads
from collections import Counter
import dateutil.parser

from src.utils import LANGUAGE_MAP
from src.models import TASK_TYPES
from tests.Setup import Setup
from tests.utils import QUESTION_MAP, get_dict_combs


class TestTask(Setup):
    filters = {
        'sort': [None, '', 'alphabetical'],
        'search': [None, '', random.choice(string.ascii_letters)],
    }

    @pytest.fixture(autouse=True)
    def setUp(self, init_db, fake_user, fake_task):
        self.set_app()
        self.tasks = []
        for i in range(5):
            self.generate_user(fake_user)
            task = self.generate_task(fake_task)
            self.tasks.append(task)
        self.tasks.sort(key=lambda x: dateutil.parser.isoparse(x['date_added']))

    def test__task_tags(self):
        tags, langs = set(), set()
        for task in self.tasks:
            tags.update(task['tags'])
            langs.update(task['languages'])

        response = self.app.get(f'/task/tags/')
        status, data = response.status_code, loads(response.data)['response']
        assert status == 200
        assert sorted(tags) == sorted(data['tags'])
        assert sorted(langs) == sorted(data['langs'])

    # @pytest.mark.xfail(reason='Something buggy is happening with date sorting')
    @pytest.mark.parametrize('filters', get_dict_combs(filters))
    def test__get_all_task(self, filters):
        endpoint = "/task/?"
        sort = filters.get('sort', 'alphabetical').strip().lower()
        search = filters.get('search', None)
        endpoint += f"sort={sort}&"
        if search is not None:
            search = search.strip().lower()
            endpoint += f"search={search}&"

        response = self.app.get(endpoint)
        status, data = response.status_code, loads(response.data)['response']

        for i in range(len(self.tasks)):
            self.tasks[i]['_id'] = self.tasks[i].pop('id', '')
            qns = self.tasks[i].pop('question_list', [])
            self.tasks[i]['question_count'] = dict(Counter(
                [QUESTION_MAP[x['question_type']] for x in qns]))
            self.tasks[i]['languages'] = [LANGUAGE_MAP[x] for x in self.tasks[i]['languages']]
            self.tasks[i].pop('details')

        if search is not None:
            self.tasks = [x for x in self.tasks if x['name'].strip().lower().startswith(search)]
        if sort == 'alphabetical':
            self.tasks.sort(key=lambda x: x['name'])

        assert status == 200
        assert data == self.tasks
