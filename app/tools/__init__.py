# app/tools/__init__.py

from .web_tools import web_fetch, tavily_search
from .wiki_search import wiki_search

from .docs_tools import (
    inspect_file,
    summarise_file,
    extract_tables,
    ocr_image,
    save_uploaded_file,
)

TOOLS = [
    tavily_search,
    web_fetch,
    wiki_search,
    inspect_file,
    summarise_file,
    extract_tables,
    ocr_image,
    save_uploaded_file,
]
