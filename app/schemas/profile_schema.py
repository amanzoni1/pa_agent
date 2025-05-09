# app/schemas/profile_schema.py

from typing import Optional, Literal, TypedDict
from pydantic import BaseModel, Field


class UpdateProfileMemory(TypedDict):
    update_type: Literal["profile"]


class Profile(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    job: Optional[str] = None
    passions: list[str] = Field(default_factory=list)
