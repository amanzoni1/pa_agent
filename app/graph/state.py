# app/graph/state.py

from langgraph.graph import MessagesState


class ChatState(MessagesState):
    # running, compressed summary of everything _before_ the last N turns
    summary: str
