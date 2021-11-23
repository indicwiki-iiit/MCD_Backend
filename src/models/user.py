from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel, validator, root_validator, Field
from typing import List, Optional, Union
from datetime import datetime

from .objectid import PydanticObjectId

USER_TYPES = ['annotator', 'problem_setter', 'reviewer', 'admin']
USER_CRITICAL_FIELDS = ['first_name', 'last_name', 'email']
ALL_USER_FIELDS = USER_CRITICAL_FIELDS + ['user_type', 'description']


class User(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    first_name: str
    last_name: str
    description: Optional[str] = ""
    email: str
    user_type: str = 'annotator'
    auth_token: str = 'UNASSIGNED'

    last_active: Optional[datetime]
    date_joined: Optional[datetime]

    review_score: float = 0.0
    annotation_score: float = 0.0
    milestone_score: float = 0.0

    @validator('user_type')
    def set_name(cls, user_type):
        if user_type in USER_TYPES:
            return user_type
        return 'annotator'

    @root_validator(pre=False)
    def remove_extra_space(cls, values):
        # removing extra spaces
        for key in ALL_USER_FIELDS + ['auth_token']:
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
