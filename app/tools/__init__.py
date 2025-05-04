# app/tools/__init__.py
from .web_search import tavily_search
from .wiki_search import wiki_search

TOOLS = [tavily_search, wiki_search]
