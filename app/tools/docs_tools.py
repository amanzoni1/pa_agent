# app/tools/docs_tools.py

import os, io
import logging
import base64
import requests
import tempfile
from typing import Optional, List, Dict, Any, Union, Literal

import pandas as pd
from PIL import Image
import pytesseract

from langchain_core.tools import tool
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
    PythonLoader,
)

logger = logging.getLogger(__name__)


def _download_to_tempfile(url: str, suffix: str) -> str:
    """Fetch a URL securely (verify TLS) and write to a NamedTemporaryFile, returning its path."""
    resp = requests.get(url, verify=True, timeout=10)
    resp.raise_for_status()
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(resp.content)
    temp.close()
    return temp.name


def _load_csv_to_df(
    path_or_url: str, delimiter: Optional[str], encoding: str
) -> pd.DataFrame:
    """
    Load a CSV into a pandas DataFrame, handling both URLs and local paths.
    """
    try:
        if path_or_url.lower().startswith(("http://", "https://")):
            resp = requests.get(path_or_url, verify=True, timeout=10)
            resp.raise_for_status()
            data = io.StringIO(resp.text)
            return pd.read_csv(data, delimiter=delimiter, encoding=encoding)
        else:
            return pd.read_csv(path_or_url, delimiter=delimiter, encoding=encoding)
    except Exception as e:
        logger.exception("Failed to load CSV %r", path_or_url)
        raise


@tool
def decode_and_save_file(
    filename: str, content_b64: str, overwrite: bool = False
) -> Union[str, dict]:
    """
    Decode a base64 blob and save it to disk, returning text or metadata.

    Args:
      filename: Local path to write.
      content_b64: Base64‐encoded string.
      overwrite: If False and file exists, returns an error.

    Returns:
      On success:
        - If UTF-8 decodable: {"text": <decoded text>}
        - Else: {"path": <filename>, "size": <bytes>}
      On failure: {"error": <message>}
    """
    try:
        if os.path.exists(filename) and not overwrite:
            return {"error": f"File {filename} already exists."}

        data = base64.b64decode(content_b64)
    except Exception as e:
        return {"error": f"Invalid base64: {e}"}

    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        with open(filename, "wb") as f:
            f.write(data)
    except Exception as e:
        logger.exception("decode_and_save_file write failed %r", filename)
        return {"error": str(e)}

    try:
        text = data.decode("utf-8")
        return {"text": text}
    except UnicodeDecodeError:
        return {"path": filename, "size_bytes": os.path.getsize(filename)}


@tool
def file_download(
    url: str, dest_path: Optional[str] = None, verify_tls: bool = True
) -> Union[str, dict]:
    """
    Download any URL to disk, with streaming, TLS verification, and metadata.

    Args:
      url: URL to fetch.
      dest_path: Local path to write. If omitted, derive from URL or Content-Disposition.
      verify_tls: Whether to verify HTTPS certificates (default True).

    Returns:
      On success: {
        'path': <dest_path>,
        'size_bytes': <int>,
        'content_type': <str>
      }
      On failure: {"error": <message>}
    """
    try:
        with requests.get(url, stream=True, verify=verify_tls, timeout=10) as resp:
            resp.raise_for_status()

            # Figure out a filename
            if dest_path is None:
                cd = resp.headers.get("content-disposition", "")
                if "filename=" in cd:
                    name = cd.split("filename=")[-1].strip("\"'")
                else:
                    name = os.path.basename(url.split("?", 1)[0])
                dest_path = name or "downloaded_file"

            # Sanitize & mkdir
            dest_dir = os.path.dirname(dest_path) or "."
            os.makedirs(dest_dir, exist_ok=True)
            filename = os.path.basename(dest_path)
            full_path = os.path.join(dest_dir, filename)

            # Stream to disk
            with open(full_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return {
            "path": full_path,
            "size_bytes": os.path.getsize(full_path),
            "content_type": resp.headers.get("content-type", ""),
        }

    except Exception as e:
        logger.exception("file_download failed for %r", url)
        return {"error": str(e)}


@tool
def read_file(path: str) -> str:
    """
    Read a local text file’s contents.
    Args:
      path: Path to the file.
    Returns:
      The full file contents or an error message.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Could not read {path}: {e}"


@tool
def extract_text_from_image(image_path: str) -> str:
    """
    Run OCR on an image file or URL and return the extracted text.

    Args:
      image_path: Local file path or HTTP(S) URL to an image (PNG, JPEG, etc.)

    Returns:
      The text extracted via pytesseract, or an error message.
    """
    try:
        # Download remote image if needed
        if image_path.lower().startswith(("http://", "https://")):
            resp = requests.get(image_path, verify=True, timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
        else:
            img = Image.open(image_path)

        # Ensure image is in a format Tesseract can handle
        img = img.convert("RGB")
        text = pytesseract.image_to_string(img)
        return text.strip()

    except Exception as e:
        logger.exception("extract_text_from_image failed for %r", image_path)
        return f"OCR error: {e}"


@tool
def handle_pdf(
    path_or_url: str,
    mode: Optional[Literal["single", "page"]] = None,
    pages_delimiter: str = "\n\n",
) -> Union[str, List[Dict[str, Any]]]:
    """
    Download and parse a PDF either as a single text flow or as page-level documents.

    Args:
      path_or_url: Local file path or HTTP(S) URL to a PDF.
      mode: 'single' to return one concatenated text, or 'page' to return list of pages.
      pages_delimiter: String marker between pages in 'single' mode.

    Returns:
      - If mode=='single': a single string of all text, pages separated by pages_delimiter.
      - If mode=='page': list of {'content': str, 'metadata': dict} for each page.
      - If mode is None or invalid: a prompt asking the user which mode they want.
    """
    # if the caller didn’t specify a mode, ask for clarification
    if mode not in ("single", "page"):
        return (
            "❓ Please let me know how to process this PDF:\n"
            "  • `mode='single'` to extract all text as one string,\n"
            "  • `mode='page'` to split into page-level documents."
        )

    try:
        source = path_or_url
        if source.lower().startswith(("http://", "https://")):
            source = _download_to_tempfile(source, suffix=".pdf")

        loader = PyPDFLoader(source, mode=mode, pages_delimiter=pages_delimiter)
        docs = loader.load()

        if mode == "single":
            return docs[0].page_content

        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]

    except Exception as e:
        logger.exception("handle_pdf failed for %r", path_or_url)
        return f"PDF parse error: {e}"


@tool
def handle_csv(
    path_or_url: str,
    mode: Literal["inspect", "columns", "docs", "html"] = "inspect",
    max_rows: int = 5,
    source_column: Optional[str] = None,
    delimiter: Optional[str] = None,
    encoding: str = "utf-8",
) -> Union[Dict[str, Any], List[Dict[str, Any]], str]:
    """
    Unified CSV handling tool using pandas.

    Args:
      path_or_url: Local file path or HTTP(S) URL to the CSV.
      mode:        'inspect' for head+stats+schema+nulls,
                   'columns' to list column types,
                   'docs' for row-wise docs,
                   'html' for HTML table string.
      max_rows:    Number of rows for 'inspect'.
      source_column: Column name for document 'source' metadata in 'docs' mode.
      delimiter:   Custom CSV delimiter (e.g. ',').
      encoding:    File encoding (default 'utf-8').

    Returns:
      - inspect: dict with 'head', 'describe', 'columns', 'null_counts'
      - columns: dict<column, dtype>
      - docs:    list of {'content': str, 'metadata': dict}
      - html:    HTML table string
    """
    try:
        df = _load_csv_to_df(path_or_url, delimiter, encoding)

        if mode == "inspect":
            return {
                "head": df.head(max_rows).to_dict(orient="records"),
                "describe": df.describe(include="all").to_dict(),
                "columns": df.dtypes.astype(str).to_dict(),
                "null_counts": df.isnull().sum().to_dict(),
            }

        if mode == "columns":
            return df.dtypes.astype(str).to_dict()

        if mode == "docs":
            docs: List[Dict[str, Any]] = []
            for idx, row in df.iterrows():
                lines = [f"{col}: {row[col]}" for col in df.columns]
                content = "\n".join(lines)
                metadata: Dict[str, Any] = {"row": int(idx)}
                if source_column and source_column in df.columns:
                    metadata["source"] = row[source_column]
                else:
                    metadata["source"] = path_or_url
                docs.append({"content": content, "metadata": metadata})
            return docs

        if mode == "html":
            return df.to_html(index=False)

        return {
            "error": f"Unknown mode '{mode}'. Use 'inspect', 'columns', 'docs', or 'html'."
        }

    except Exception as e:
        return {"error": str(e)}


@tool
def excel_inspect(
    excel_path: str,
    sheet_name: Optional[str] = None,
    max_rows: int = 5,
) -> Dict[str, Any]:
    """
    Load an Excel file (local path or URL), pick a sheet, and return its head + summary stats.

    Args:
      excel_path: Path or URL to a .xlsx/.xls file.
      sheet_name: Name of the sheet (defaults to the first).
      max_rows:   Number of rows in the “head” output.

    Returns:
      {
        "sheet":    sheet_name_used,
        "head":     [ {column: value, …}, … ],
        "describe": { statistic: { column: value, … }, … }
      }
      or {"error": ...} on failure.
    """
    try:
        # fetch remote if needed
        if excel_path.lower().startswith(("http://", "https://")):
            resp = requests.get(excel_path, verify=False, timeout=10)
            resp.raise_for_status()
            data = io.BytesIO(resp.content)
            xls = pd.ExcelFile(data)
        else:
            xls = pd.ExcelFile(excel_path)

        sheet = sheet_name or xls.sheet_names[0]
        df = xls.parse(sheet)

        return {
            "sheet": sheet,
            "head": df.head(max_rows).to_dict(orient="records"),
            "describe": df.describe(include="all").to_dict(),
        }
    except Exception as e:
        logger.exception("excel_inspect failed for %r", excel_path)
        return {"error": str(e)}


@tool
def list_dir(path: str, recursive: bool = False) -> List[str]:
    """
    List files in a directory.
    Args:
      path: Directory path.
      recursive: If True, walk subdirectories.
    Returns:
      A list of file paths.
    """
    files = []
    if recursive:
        for root, _, filenames in os.walk(path):
            for fn in filenames:
                files.append(os.path.join(root, fn))
    else:
        for fn in os.listdir(path):
            files.append(os.path.join(path, fn))
    return files


@tool
def handle_directory(
    path: str,
    pattern: str = "**/*",
    mode: Literal['docs','snippets','text','list'] = 'docs',
    max_files: int = 20,
    snippet_chars: int = 500,
    show_progress: bool = False,
    use_multithreading: bool = False,
    loader_cls: Optional[str] = None,
    loader_kwargs: Optional[Dict[str, Any]] = None,
    silent_errors: bool = False,
) -> Union[List[Any], str, Dict[str, Any]]:
    """
    Unified directory loader for text-based documents.

    Args:
      path: Local directory path.
      pattern: Glob pattern for files (e.g. "**/*.md").
      mode: 'docs','snippets','text','list'.
      max_files: Max docs/snippets when mode in ['docs','snippets'].
      snippet_chars: Chars per snippet.
      show_progress: Use tqdm progress bar.
      use_multithreading: Enable multithreading.
      loader_cls: One of 'UnstructuredFileLoader','TextLoader','PythonLoader'.
      loader_kwargs: Extra kwargs for loader class.
      silent_errors: Skip files that error.

    Returns:
      Depending on mode:
        - list: [source_path,...]
        - docs: [{content,metadata},...]
        - snippets: [{source,snippet},...]
        - text: str concatenation
        - error: dict{error:...}
    """
    try:
        cls_map = {
            'UnstructuredFileLoader': UnstructuredFileLoader,
            'TextLoader': TextLoader,
            'PythonLoader': PythonLoader,
        }
        chosen_loader = cls_map.get(loader_cls) if loader_cls else None

        loader_params = {
            'glob': pattern,
            'show_progress': show_progress,
            'use_multithreading': use_multithreading,
            'silent_errors': silent_errors,
        }
        if chosen_loader:
            loader_params['loader_cls'] = chosen_loader
        if loader_kwargs:
            loader_params['loader_kwargs'] = loader_kwargs
        loader = DirectoryLoader(path, **loader_params)
        docs = loader.load()

        if mode == 'list':
            return [d.metadata.get('source', '') for d in docs]

        if mode == 'docs':
            out = []
            for d in docs[:max_files]:
                meta = dict(d.metadata)
                meta['source'] = meta.get('source', '')
                out.append({'content': d.page_content, 'metadata': meta})
            return out

        if mode == 'snippets':
            snippets = []
            for d in docs[:max_files]:
                text = d.page_content.replace('', ' ')[:snippet_chars]
                source = d.metadata.get('source', '')
                snippets.append({'source': source, 'snippet': text})
            return snippets

        if mode == 'text':
            return ''.join(d.page_content for d in docs)

        return {'error': f"Unknown mode '{mode}'"}

    except Exception as e:
        logger.exception("handle_directory failed for %r", path)
        return {'error': str(e)}
