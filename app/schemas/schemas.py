from datetime import date
from typing import Optional, List, Literal, TypedDict
from pydantic import BaseModel, Field


class UpdateMemory(TypedDict):
    """Tells the router which slice of the profile to update."""

    update_type: Literal["profile", "memories", "projects", "instructions"]


class Profile(BaseModel):
    """Core, factual info about the user."""

    name: Optional[str] = None
    location: Optional[str] = None
    job: Optional[str] = None

    passions: List[str] = Field(
        default_factory=list,
        description="What the user is truly passionate about (e.g. hiking, painting, chess).",
    )
    goals: List[str] = Field(
        default_factory=list,
        description="Longer-term goals or ambitions the user has mentioned.",
    )


class Memory(BaseModel):
    """A single episodic memory or fact from conversation."""

    content: str
    tags: Optional[List[str]] = Field(
        default=None,
        description="Optional labels like 'travel', 'health', 'family' for quick filtering.",
    )


class Project(BaseModel):
    """A plan or project the user wants to track."""

    title: str = Field(..., description="Short name of the project or plan.")
    description: Optional[str] = Field(
        default=None, description="A more detailed description or context."
    )
    due_date: Optional[date] = Field(
        default=None, description="If the user gave a deadline (e.g. 'by June 1')."
    )
    status: Literal["planned", "in progress", "completed"] = Field(
        default="planned", description="Where they stand on this project."
    )


class UserProfile(BaseModel):
    """
    Everything we know about the user in one document.

    - `profile`: core facts + their passions & goals
    - `memories`: important conversation snippets over time
    - `projects`: concrete plans/tasks they’re tracking
    - `instructions`: any special preferences for how you should behave
    """

    profile: Profile = Field(default_factory=Profile)
    memories: List[Memory] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    instructions: Optional[str] = Field(
        default=None,
        description="User’s meta-preferences (e.g. 'always suggest local vendors').",
    )
