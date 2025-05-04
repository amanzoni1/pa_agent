# app/schemas/project_schema.py

from typing import TypedDict, Optional, Literal
from datetime import date
from pydantic import BaseModel


class UpdateProjectMemory(TypedDict):
    update_type: Literal["projects"]


class Project(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Literal["planned", "in progress", "completed"] = "planned"
