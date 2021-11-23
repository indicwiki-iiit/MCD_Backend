import io
import os
import pytest
import random
import json

from faker import Faker
from unittest.mock import patch
from mongomock import MongoClient

import src.database as db
from src.models import USER_TYPES, QUESTION_TYPES, TASK_TYPES

fake = Faker()


@pytest.fixture()
def init_db():
    with patch.object(db, "mongo_db", MongoClient().db):
        assert db.mongo_db == MongoClient().db
        yield


@pytest.fixture()
def fake_user():
    return lambda: {
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'email': fake.email(),
        'description': fake.text(),
        'user_type': random.choice(USER_TYPES),
    }


@pytest.fixture()
def fake_task(fake_user):
    with open(os.path.join(os.getcwd(), 'resources/questions.jsonl'), 'rb') as f:
        qn_bytes = f.read()
    with open(os.path.join(os.getcwd(), 'resources/questions.jsonl'), 'r') as f:
        questions = [json.loads(x) for x in f]

    return lambda: {
        'name': fake.name(),
        'short_description': fake.sentence(),
        'details': fake.text(),
        'tags': fake.words(random.randint(1, 5)),
        'question_list': questions,
        'reward_levels': random.sample(range(1, 50), 3),
        'access_type': random.choice(TASK_TYPES),
        'file': (io.BytesIO(qn_bytes), 'test.jsonl'),
    }


@pytest.fixture()
def fake_response():
    return lambda: {
        'response': [fake.sentence()],
        'response_type': random.choice(QUESTION_TYPES)
    }
