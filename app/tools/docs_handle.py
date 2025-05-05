# app/tools/docs_handle.py

import os, io
import logging
import base64
import requests
import tempfile
from typing import Optional, List, Dict, Any

import pandas as pd
from PIL import Image
import pytesseract

from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader

logger = logging.getLogger(__name__)


def _download_to_tempfile(url: str, suffix: str) -> str:
    """Fetch a URL and write to a NamedTemporaryFile, return its path."""
    resp = requests.get(url, verify=False, timeout=10)
    resp.raise_for_status()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tf.write(resp.content)
    tf.close()
    return tf.name


@tool
def decode_and_save_file(filename: str, content_b64: str) -> str:
    """
    Decode a base64‐encoded blob and save it to `filename`.

    Args:
      filename: Path (including filename) to write the decoded bytes.
      content_b64: A base64‐encoded string.

    Returns:
      - If the bytes decode as UTF‑8, returns the decoded text.
      - Otherwise returns a confirmation that the binary was written.
    """
    try:
        data = base64.b64decode(content_b64)
    except Exception as e:
        return f"⚠️ Invalid base64 content: {e}"

    try:
        with open(filename, "wb") as f:
            f.write(data)
    except Exception as e:
        logger.exception("decode_and_save_file: failed to write %r", filename)
        return f"⚠️ Could not write file {filename}: {e}"

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return f"✅ Wrote binary file to {filename}"


@tool
def file_download(url: str, dest_path: Optional[str] = None) -> str:
    """
    Download a URL’s bytes and save to `dest_path` (or auto‐derived filename).

    Args:
      url: The URL to fetch.
      dest_path: Optional local path. If omitted, the filename is derived from the URL.

    Returns:
      The path to the saved file, or an error message on failure.
    """
    if dest_path is None:
        dest_path = os.path.basename(url.split("?", 1)[0]) or "downloaded_file"
    try:
        resp = requests.get(url, verify=False, timeout=10)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path
    except Exception as e:
        logger.exception("file_download failed for %r", url)
        return f"⚠️ Download error: {e}"


@tool
def extract_text_from_image(image_path: str) -> str:
    """
    Run OCR on an image file and return the extracted text.

    Args:
      image_path: Path to a local image (PNG, JPEG, etc.)

    Returns:
      The text extracted via pytesseract, or an error message.
    """
    try:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img)
    except Exception as e:
        logger.exception("extract_text_from_image failed for %r", image_path)
        return f"⚠️ OCR error: {e}"


@tool
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF (local path or URL) via PyPDFLoader.

    Args:
      pdf_path: Local file path or HTTP(S) URL to a PDF.

    Returns:
      The entire text (pages concatenated with two newlines), or an error message.
    """
    try:
        # if remote, download first
        if pdf_path.lower().startswith(("http://", "https://")):
            pdf_path = _download_to_tempfile(pdf_path, ".pdf")

        loader = PyPDFLoader(pdf_path, mode="single")
        docs = loader.load()
        # single mode always returns a list of length 1
        return docs[0].page_content

    except Exception as e:
        logger.exception("extract_text_from_pdf failed for %r", pdf_path)
        return f"⚠️ PDF parse error: {e}"


@tool
def csv_inspect(csv_path: str, max_rows: int = 5) -> Dict[str, Any]:
    """
    Load a CSV (local file or URL) and return its first rows plus summary statistics.

    Args:
      csv_path: Path or URL to a CSV file.
      max_rows: Number of rows to include in the “head” output.

    Returns:
      {
        "head":    [ {column: value, …}, … ],
        "describe": { statistic: { column: value, … }, … }
      }
      or {"error": ...} on failure.
    """
    try:
        # if it's a URL, fetch it first
        if csv_path.lower().startswith(("http://", "https://")):
            resp = requests.get(csv_path, verify=False, timeout=10)
            resp.raise_for_status()
            data = io.StringIO(resp.text)
            df = pd.read_csv(data)
        else:
            df = pd.read_csv(csv_path)

        return {
            "head": df.head(max_rows).to_dict(orient="records"),
            "describe": df.describe(include="all").to_dict(),
        }
    except Exception as e:
        logger.exception("csv_inspect failed for %r", csv_path)
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
def dir_snippets(directory: str, max_files: int = 20) -> List[Dict[str, Any]]:
    """
    Recursively load documents from a directory and return short text snippets.

    Args:
      directory: Path to a local directory.
      max_files: Maximum documents to load.

    Returns:
      [ { "source": <file path>, "snippet": <first 500 chars> }, … ]
      or [] on failure.
    """
    try:
        loader = DirectoryLoader(directory, recursive=True)
        docs = loader.load()
        output = []
        for d in docs[:max_files]:
            text = d.page_content.replace("\n", " ")[:500]
            output.append({"source": d.metadata.get("source", ""), "snippet": text})
        return output
    except Exception as e:
        logger.exception("dir_snippets failed for %r", directory)
        return []


@tool
def read_dir_text(path: str, pattern: str = "**/*") -> str:
    """
    Load all files matching a glob pattern in a directory and return their full text.

    Args:
      path: Local directory path.
      pattern: Glob pattern (e.g. "**/*.md").

    Returns:
      Concatenated text of every loaded document, or an error message.
    """
    try:
        loader = DirectoryLoader(path, glob=pattern)
        docs = loader.load()
        return "\n\n".join(d.page_content for d in docs)
    except Exception as e:
        logger.exception("read_dir_text failed for %r", path)
        return f"⚠️ Directory load error: {e}"
