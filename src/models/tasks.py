from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel, validator, root_validator, Field
from typing import List, Optional, Union
from datetime import datetime

from .objectid import PydanticObjectId

QUESTION_TYPES = ['text', 'mcq-single-correct', 'mcq-multiple-correct', 'translation']
QUESTION_LEVELS = {'easy': 0, 'medium': 1, 'hard': 2}
TASK_CRITICAL_FIELDS = ['name', 'short_description',
                        'details', 'question_list', 'problem_setter_id', 'tags']
ALL_TASK_FIELDS = TASK_CRITICAL_FIELDS + ['reward_levels', 'access_type']
TASK_TYPES = ['global-view', 'single-view']

DEFAULT_MIN_QUESTIONS = 1
DEFAULT_MAX_QUESTIONS = 10

QUESTION_DISP_NAME = {
    'text': "Descriptive",
    'mcq-single-correct': "MCQ",
    'mcq-multiple-correct': "MCQ multiple correct",
    'translation': "Translation"
}


class Question(BaseModel):
    id: str
    question_prompt: str
    question_type: str
    question_level: str = 'medium'
    review_flag: bool = False
    question_contexts: List[str] = []
    response_options: List[str] = []
    language: str = 'en'
    text_input_language: Optional[str]
    default_value: Optional[str]
    assigned: str = ''
    session_id: int = 0
    seqno: int

    @validator('question_level')
    def is_level_valid(cls, question_level):
        question_level = question_level.strip()
        if question_level not in QUESTION_LEVELS:
            raise ValueError('%s general_question_api-level is not valid.' %
                             question_level)
        return question_level

    @validator('question_type')
    def is_type_valid(cls, question_type):
        question_type = question_type.strip()
        if question_type not in QUESTION_TYPES:
            raise ValueError('%s general_question_api-type is not valid.' % question_type)
        return question_type

    @root_validator(pre=False)
    def mcq_question_validator(cls, values):
        instance_question_type = values.get('question_type').strip()
        instance_response_options = values.get('response_options')
        if instance_question_type.startswith('mcq') and len(instance_response_options) == 0:
            raise ValueError(
                'multi-choice general_question_api type with single correct response is not valid with zero options')

        # removing extra spaces
        for key in ['question_prompt', 'language']:
            temp_val = values[key]
            values[key] = temp_val.strip()
        return values

    def to_json(self):
        return jsonable_encoder(self, exclude_none=True)

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data


class Task(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    name: str
    short_description: str
    details: Optional[str] = ''
    reward_levels: List[float] = [10, 10, 10]
    languages: List[str] = ['en']
    question_list: Optional[List[Question]] = []
    problem_setter_id: str
    tags: List[str] = []
    date_added: datetime
    date_modified: datetime
    access_type: str = 'global-view'
    min_question_count: int = DEFAULT_MIN_QUESTIONS
    max_question_count: int = DEFAULT_MAX_QUESTIONS

    @root_validator
    def remove_extra_spaces(cls, values):
        # qlist = values.get('question_list', [])
        # if len(qlist) == 0:
        #     raise ValueError(
        #         "question_list should contain atleast one general_question_api")

        # removing extra spaces
        for key in ['name', 'short_description', 'details', 'problem_setter_id']:
            temp_val = values[key]
            values[key] = temp_val.strip()
        return values

    @validator('reward_levels')
    def check_rewards_lengths(cls, rewards):
        if len(rewards) != 3:
            return [10, 10, 10]
        return rewards

    @validator('access_type')
    def is_type_valid(cls, type):
        type = type.strip()
        if type not in TASK_TYPES:
            raise ValueError('%s task_api-type is not valid.' % type)
        return type

    def to_json(self):
        return jsonable_encoder(self, exclude_none=True)

    def to_bson(self):
        data = self.dict(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
