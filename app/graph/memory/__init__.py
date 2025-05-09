# app/graph/nodes/__init__.py

from .profile_node import update_user_profile
from .projects_node import update_projects
from .instructions_node import update_instructions

MEMORY = [
    update_user_profile,
    update_projects,
    update_instructions,
]
