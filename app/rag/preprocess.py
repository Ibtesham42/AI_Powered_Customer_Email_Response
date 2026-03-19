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



# GLOBAL


documents = []
MAX_TEXT_LENGTH = 2000



# CLEANING FUNCTIONS (UPGRADED)


def clean_html(text):

    if not text:
        return ""

    soup = BeautifulSoup(str(text), "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    return soup.get_text(separator=" ")


def remove_sensitive(text):

    patterns = [
        r"password\s*[:=]\s*\S+",
        r"ftp\s*[:=]\s*\S+",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"https?://\S+",
    ]

    for p in patterns:
        text = re.sub(p, "[REDACTED]", text, flags=re.I)

    return text


#
# PDF / NOISE CLEANING


def clean_noise(text):

    text = str(text)

    # remove hashes / ids
    text = re.sub(r'\b[a-f0-9]{6,}\b', '', text)

    # remove repeated words
    text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text)

    # remove single letters
    text = re.sub(r'\b[a-zA-Z]\b', '', text)

    # remove numbers only
    text = re.sub(r'\b\d+\b', '', text)

    # remove system junk
    junk_words = [
        "ticketid", "adminr", "userid", "contactid",
        "merged", "_ticket_id", "depart", "priority",
        "status", "service", "ticketkey", "project_id",
        "clientread", "adminread", "assigned",
        "staff_id", "replying"
    ]

    for word in junk_words:
        text = re.sub(word, '', text, flags=re.IGNORECASE)

    return text


def normalize_value(value):

    if pd.isna(value):
        return "NULL"

    if isinstance(value, float):
        return str(round(value, 2))

    return str(value)


def clean_text(text):

    text = clean_html(text)
    text = remove_sensitive(text)
    text = clean_noise(text)

    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    return text



# CHUNKING + FILTERING 


def chunk_text(text):

    chunks = re.split(r'\n{2,}|\.\s', text)

    chunks = [c.strip() for c in chunks if len(c) > 40]

    return chunks


def filter_meaningful_chunks(chunks):

    keywords = [
        "please", "issue", "email", "request",
        "help", "need", "confirm", "delay",
        "add", "sent"
    ]

    return [
        c for c in chunks
        if any(k in c.lower() for k in keywords)
    ]



# ADD DOCUMENT SAFE


def add_document(text, metadata):

    if not text or len(text) < 10:
        return

    documents.append({
        "doc_id": len(documents) + 1,
        "text": text,
        "metadata": metadata
    })



# CSV PROCESSOR (UPGRADED)


def process_csv(file_path):

    df = pd.read_csv(file_path)
    df = df.fillna("NULL")

    for _, row in df.iterrows():

        text_parts = []

        for col in df.columns:
            value = normalize_value(row[col])
            text_parts.append(f"{col}: {value}")

        text = "\n".join(text_parts)

        text = clean_text(text)

        chunks = chunk_text(text)
        chunks = filter_meaningful_chunks(chunks)

        for c in chunks:
            add_document(c, {
                "source": "csv",
                "file": os.path.basename(file_path)
            })



# PDF PROCESSOR 


def process_pdf(file_path):

    reader = PdfReader(file_path)

    full_text = ""

    for page in reader.pages:
        try:
            full_text += page.extract_text() or ""
        except:
            continue

    full_text = clean_text(full_text)

    chunks = chunk_text(full_text)
    chunks = filter_meaningful_chunks(chunks)

    for i, c in enumerate(chunks):
        add_document(c, {
            "source": "pdf",
            "file": os.path.basename(file_path),
            "chunk": i
        })



# TXT PROCESSOR


def process_txt(file_path):

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    text = clean_text(text)

    chunks = chunk_text(text)

    for c in chunks:
        add_document(c, {
            "source": "txt",
            "file": os.path.basename(file_path)
        })



# DOCX PROCESSOR


def process_docx(file_path):

    doc = Document(file_path)

    text = "\n".join([p.text for p in doc.paragraphs])

    text = clean_text(text)

    chunks = chunk_text(text)

    for c in chunks:
        add_document(c, {
            "source": "docx",
            "file": os.path.basename(file_path)
        })



# JSON PROCESSOR


def process_json(file_path):

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    for item in data:

        raw_text = item.get("text", "")

        text = clean_text(raw_text)

        chunks = chunk_text(text)

        for c in chunks:
            add_document(c, {
                "source": "json",
                "file": os.path.basename(file_path),
                **item.get("metadata", {})
            })



# MAIN


def preprocess(user_id):

    global documents
    documents = []

    workspace = WorkspaceManager(user_id)

    RAW_FOLDER = workspace.raw()
    OUTPUT = workspace.processed() + "/documents.json"

    Path(workspace.processed()).mkdir(parents=True, exist_ok=True)

    files = os.listdir(RAW_FOLDER)

    seen_texts = set()

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

    
    # REMOVE DUPLICATES
    

    unique_docs = []

    for doc in documents:
        if doc["text"] not in seen_texts:
            seen_texts.add(doc["text"])
            unique_docs.append(doc)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(unique_docs, f, indent=2, ensure_ascii=False)

    print("Total documents created:", len(unique_docs))



# ENTRY POINT


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", required=True)

    args = parser.parse_args()

    preprocess(args.user_id)