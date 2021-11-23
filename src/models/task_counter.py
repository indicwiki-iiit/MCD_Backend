# from fastapi.encoders import jsonable_encoder
#
# from pydantic import BaseModel, validator, root_validator, Field
# from typing import List, Optional, Union
# from datetime import datetime
#
# from .objectid import PydanticObjectId
#
#
# class Response(BaseModel):
#     id: Optional[PydanticObjectId] = Field(None, alias="_id")
#     task_id: str
#     user_id: str
#     language: str
#     seqno: int = 0
#
#     def to_json(self):
#         return jsonable_encoder(self, exclude_none=True)
#
#     def to_bson(self):
#         data = self.dict(by_alias=True, exclude_none=True)
#         if data.get("_id") is None:
#             data.pop("_id", None)
#         return data
