import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import os
import re
import json
import pandas as pd
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document

from app.utils.workspace_manager import WorkspaceManager


documents = []


def clean_html(text):

    if not text:
        return ""

    soup = BeautifulSoup(str(text), "html.parser")
    return soup.get_text(separator=" ")


def remove_sensitive(text):

    patterns = [
        r"password\s*[:=]\s*\S+",
        r"pass\s*[:=]\s*\S+",
        r"ftp\s*[:=]\s*\S+",
    ]

    for p in patterns:
        text = re.sub(p, "[REDACTED]", text, flags=re.I)

    return text


def clean_text(text):

    text = clean_html(text)
    text = remove_sensitive(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================
# CSV PROCESSOR
# =========================

def process_csv(file_path):

    df = pd.read_csv(file_path)

    for _, row in df.iterrows():

        text_parts = []

        for col in df.columns:

            value = row[col]

            if pd.notna(value):

                text_parts.append(f"{col}: {value}")

        text = "\n".join(text_parts)

        text = clean_text(text)

        documents.append({

            "doc_id": len(documents) + 1,

            "text": text,

            "metadata": {
                "source": "csv",
                "file": os.path.basename(file_path)
            }

        })


# =========================
# PDF PROCESSOR
# =========================

def process_pdf(file_path):

    reader = PdfReader(file_path)

    for i, page in enumerate(reader.pages):

        text = page.extract_text()

        text = clean_text(text)

        documents.append({

            "doc_id": len(documents) + 1,

            "text": text,

            "metadata": {
                "source": "pdf",
                "file": os.path.basename(file_path),
                "page": i
            }

        })


# =========================
# TXT PROCESSOR
# =========================

def process_txt(file_path):

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    text = clean_text(text)

    documents.append({

        "doc_id": len(documents) + 1,

        "text": text,

        "metadata": {
            "source": "txt",
            "file": os.path.basename(file_path)
        }

    })


# =========================
# DOCX PROCESSOR
# =========================

def process_docx(file_path):

    doc = Document(file_path)

    text = "\n".join([p.text for p in doc.paragraphs])

    text = clean_text(text)

    documents.append({

        "doc_id": len(documents) + 1,

        "text": text,

        "metadata": {
            "source": "docx",
            "file": os.path.basename(file_path)
        }

    })


# =========================
# JSON PROCESSOR
# =========================

def process_json(file_path):

    with open(file_path) as f:
        data = json.load(f)

    for item in data:

        text = clean_text(item.get("text", ""))

        documents.append({

            "doc_id": item.get("doc_id", len(documents) + 1),

            "text": text,

            "metadata": item.get("metadata", {})

        })


# =========================
# MAIN
# =========================

def preprocess(user_id):

    workspace = WorkspaceManager(user_id)

    RAW_FOLDER = workspace.raw()

    OUTPUT = workspace.processed() + "/documents.json"

    Path(workspace.processed()).mkdir(parents=True, exist_ok=True)

    files = os.listdir(RAW_FOLDER)

    for file in files:

        path = os.path.join(RAW_FOLDER, file)

        if file.endswith(".csv"):

            print("Processing CSV:", file)

            process_csv(path)

        elif file.endswith(".pdf"):

            print("Processing PDF:", file)

            process_pdf(path)

        elif file.endswith(".txt"):

            process_txt(path)

        elif file.endswith(".json"):

            process_json(path)

        elif file.endswith(".docx"):

            process_docx(path)

    with open(OUTPUT, "w") as f:

        json.dump(documents, f, indent=2)

    print("Total documents created:", len(documents))


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--user_id", required=True)

    args = parser.parse_args()

    preprocess(args.user_id)