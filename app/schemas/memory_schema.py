# app/schemas/memory_schema.py

from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel, Field


class UpdateExperienceMemory(TypedDict):
    update_type: Literal["memories"]


class Memory(BaseModel):
    content: str
    tags: Optional[List[str]] = None
