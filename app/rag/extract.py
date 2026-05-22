"""Plain-text extraction from knowledge-base files.

Returns lightly-cleaned text — only whitespace is normalised. Aggressive
cleaning is deliberately avoided so policy and FAQ content (numbers, short
lines, identifiers) survives intact; chunking happens downstream.
"""

import csv
import json
import re
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

# File extensions accepted as knowledge-base sources.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".json"}


class UnsupportedFileType(Exception):
    """The file's extension is not a supported knowledge-base format."""


def _normalise(text: str) -> str:
    """Collapse runs of whitespace while keeping paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(path: str) -> str:
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # skip an unreadable page, keep the rest
            continue
    return "\n\n".join(parts)


def _extract_docx(path: str) -> str:
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_txt(path: str) -> str:
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_csv(path: str) -> str:
    """Render each row as ``column: value`` lines — a stable textual form."""
    rows = []
    with open(path, encoding="utf-8", errors="ignore", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                "\n".join(f"{k}: {v}" for k, v in row.items() if k and v)
            )
    return "\n\n".join(rows)


def _extract_json(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    def walk(obj) -> list[str]:
        if isinstance(obj, dict):
            return [s for v in obj.values() for s in walk(v)]
        if isinstance(obj, list):
            return [s for v in obj for s in walk(v)]
        return [str(obj)]

    return "\n".join(walk(data))


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
    ".csv": _extract_csv,
    ".json": _extract_json,
}


def extract_text(path: str) -> str:
    """Extract plain text from a knowledge-base file.

    Raises ``UnsupportedFileType`` if the extension is not supported.
    """
    ext = Path(path).suffix.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise UnsupportedFileType(f"Unsupported file type: {ext!r}")
    return _normalise(extractor(path))
