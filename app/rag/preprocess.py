import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import re
import json
import pandas as pd
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document

from app.utils.workspace_manager import WorkspaceManager


# ------------------------------
# GLOBAL
# ------------------------------

documents = []
MAX_TEXT_LENGTH = 2000   # prevent huge chunks


# ------------------------------
# CLEANING FUNCTIONS
# ------------------------------

def clean_html(text):

    if not text:
        return ""

    soup = BeautifulSoup(str(text), "html.parser")

    # remove script/style
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    return text


def remove_sensitive(text):

    patterns = [
        r"password\s*[:=]\s*\S+",
        r"pass\s*[:=]\s*\S+",
        r"ftp\s*[:=]\s*\S+",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",  # emails
        r"https?://\S+",  # URLs
    ]

    for p in patterns:
        text = re.sub(p, "[REDACTED]", text, flags=re.I)

    return text


def normalize_value(value):

    if pd.isna(value):
        return "NULL"

    # numbers safe convert
    if isinstance(value, float):
        return str(round(value, 2))

    return str(value)


def clean_text(text):

    text = clean_html(text)
    text = remove_sensitive(text)

    text = re.sub(r"\s+", " ", text)

    text = text.strip()

    # limit size (important for RAG)
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    return text


# ------------------------------
# ADD DOCUMENT SAFE
# ------------------------------

def add_document(text, metadata):

    if not text or len(text) < 10:
        return

    documents.append({
        "doc_id": len(documents) + 1,
        "text": text,
        "metadata": metadata
    })


# ------------------------------
# CSV PROCESSOR (IMPROVED)
# ------------------------------

def process_csv(file_path):

    df = pd.read_csv(file_path)

    df = df.fillna("NULL")   # handle null properly

    for _, row in df.iterrows():

        text_parts = []

        for col in df.columns:

            value = normalize_value(row[col])

            text_parts.append(f"{col}: {value}")

        text = "\n".join(text_parts)

        text = clean_text(text)

        add_document(text, {
            "source": "csv",
            "file": os.path.basename(file_path)
        })


# ------------------------------
# PDF PROCESSOR (SAFE)
# ------------------------------

def process_pdf(file_path):

    reader = PdfReader(file_path)

    for i, page in enumerate(reader.pages):

        try:
            text = page.extract_text() or ""
        except:
            text = ""

        text = clean_text(text)

        add_document(text, {
            "source": "pdf",
            "file": os.path.basename(file_path),
            "page": i
        })


# ------------------------------
# TXT PROCESSOR
# ------------------------------

def process_txt(file_path):

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = clean_text(text)

    add_document(text, {
        "source": "txt",
        "file": os.path.basename(file_path)
    })


# ------------------------------
# DOCX PROCESSOR
# ------------------------------

def process_docx(file_path):

    doc = Document(file_path)

    text = "\n".join([p.text for p in doc.paragraphs])

    text = clean_text(text)

    add_document(text, {
        "source": "docx",
        "file": os.path.basename(file_path)
    })


# ------------------------------
# JSON PROCESSOR
# ------------------------------

def process_json(file_path):

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    for item in data:

        raw_text = item.get("text", "")

        text = clean_text(raw_text)

        add_document(text, {
            "source": "json",
            "file": os.path.basename(file_path),
            **item.get("metadata", {})
        })


# ------------------------------
# MAIN
# ------------------------------

def preprocess(user_id):

    global documents
    documents = []   # IMPORTANT (multi-user safe)

    workspace = WorkspaceManager(user_id)

    RAW_FOLDER = workspace.raw()
    OUTPUT = workspace.processed() + "/documents.json"

    Path(workspace.processed()).mkdir(parents=True, exist_ok=True)

    files = os.listdir(RAW_FOLDER)

    seen_texts = set()   # deduplication

    for file in files:

        path = os.path.join(RAW_FOLDER, file)

        print(f"Processing: {file}")

        if file.endswith(".csv"):
            process_csv(path)

        elif file.endswith(".pdf"):
            process_pdf(path)

        elif file.endswith(".txt"):
            process_txt(path)

        elif file.endswith(".json"):
            process_json(path)

        elif file.endswith(".docx"):
            process_docx(path)

    # ------------------------------
    # REMOVE DUPLICATES
    # ------------------------------

    unique_docs = []

    for doc in documents:
        if doc["text"] not in seen_texts:
            seen_texts.add(doc["text"])
            unique_docs.append(doc)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(unique_docs, f, indent=2, ensure_ascii=False)

    print("Total documents created:", len(unique_docs))


# ------------------------------
# ENTRY POINT
# ------------------------------

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", required=True)

    args = parser.parse_args()

    preprocess(args.user_id)