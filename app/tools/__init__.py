# app/tools/__init__.py

from .web_tools import web_fetch, tavily_search
from .wiki_search import wiki_search

from .docs_tools import (
    decode_and_save_file,
    file_download,
    read_file,
    extract_text_from_image,
    handle_pdf,
    handle_csv,
    excel_inspect,
    list_dir,
    handle_directory,
)

TOOLS = [
    tavily_search,
    web_fetch,
    wiki_search,
    decode_and_save_file,
    file_download,
    read_file,
    extract_text_from_image,
    handle_pdf,
    handle_csv,
    excel_inspect,
    list_dir,
    handle_directory,
]
