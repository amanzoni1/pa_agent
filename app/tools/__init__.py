# app/tools/__init__.py

from .web_search import tavily_search
from .web_loader import web_fetch
from .wiki_search import wiki_search

from .docs_handle import (
    decode_and_save_file,
    file_download,
    extract_text_from_image,
    extract_text_from_pdf,
    csv_inspect,
    excel_inspect,
    dir_snippets,
    read_dir_text,
)

from .docs_loader import (
    csv_to_docs,
    unstructured_csv_to_docs,
    pdf_to_docs,
    dir_to_docs,
)

TOOLS = [
    # — Web / Retrieval —
    tavily_search,
    web_fetch,
    wiki_search,
    # — File I/O Utilities —
    decode_and_save_file,
    file_download,
    # — OCR & PDF/Text Extraction —
    extract_text_from_image,
    extract_text_from_pdf,
    # — Tabular Inspection —
    csv_inspect,
    excel_inspect,
    # — Directory Utilities —
    dir_snippets,
    read_dir_text,
    # — Document‐to‐“Document” loaders (for retrieval pipelines) —
    csv_to_docs,
    unstructured_csv_to_docs,
    pdf_to_docs,
    dir_to_docs,
]
