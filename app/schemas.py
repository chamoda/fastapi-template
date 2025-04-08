from typing import Annotated
from pydantic import BaseModel, ConfigDict, NaiveDatetime, WrapSerializer

DateTime = Annotated[
    NaiveDatetime, WrapSerializer(lambda v, nxt: f"{nxt(v)}Z", when_used="json")
]


class Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
