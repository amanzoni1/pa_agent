# app/schemas/memory_schema.py

from typing import TypedDict, Literal
from pydantic import BaseModel
# from langgraph.graph.message import add_messages


class UpdateInstructionMemory(TypedDict):
    update_type: Literal["instructions"]


class Instruction(BaseModel):
    content: str
