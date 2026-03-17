import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import json
from pathlib import Path
import os

from pypdf import PdfReader
from docx import Document

from app.utils.workspace_manager import WorkspaceManager


documents = []


def process_csv(file_path):

    df = pd.read_csv(file_path)

    for _, row in df.iterrows():

        text = f"""
Customer ID: {row.get('customer_id','')}
Customer Email: {row.get('customer_email','')}
Order ID: {row.get('order_id','')}
Product: {row.get('product_name','')}
Order Status: {row.get('order_status','')}
Payment Status: {row.get('payment_status','')}
Invoice ID: {row.get('invoice_id','')}
Ticket ID: {row.get('ticket_id','')}

Title: {row.get('title','')}
Content: {row.get('content','')}
"""

        documents.append({
            "doc_id": int(row.get("doc_id", len(documents)+1)),
            "text": text.strip(),
            "metadata": {
                "source": "csv",
                "customer_email": row.get("customer_email",""),
                "order_id": row.get("order_id","")
            }
        })


def process_pdf(file_path):

    reader = PdfReader(file_path)

    for i, page in enumerate(reader.pages):

        text = page.extract_text()

        documents.append({
            "doc_id": len(documents)+1,
            "text": text,
            "metadata": {
                "source": "pdf",
                "file": os.path.basename(file_path),
                "page": i
            }
        })


def process_txt(file_path):

    with open(file_path, "r", encoding="utf-8") as f:

        text = f.read()

    documents.append({
        "doc_id": len(documents)+1,
        "text": text,
        "metadata": {
            "source": "txt",
            "file": os.path.basename(file_path)
        }
    })


def process_json(file_path):

    with open(file_path) as f:

        data = json.load(f)

    for item in data:

        documents.append({
            "doc_id": item.get("doc_id", len(documents)+1),
            "text": item.get("text",""),
            "metadata": item.get("metadata",{})
        })


def process_docx(file_path):

    doc = Document(file_path)

    text = "\n".join([p.text for p in doc.paragraphs])

    documents.append({
        "doc_id": len(documents)+1,
        "text": text,
        "metadata": {
            "source": "docx",
            "file": os.path.basename(file_path)
        }
    })


def preprocess(user_id):
    documents.clear()
    workspace = WorkspaceManager(user_id)

    RAW_FOLDER = workspace.raw()
    OUTPUT = workspace.processed() + "/documents.json"

    Path(workspace.processed()).mkdir(parents=True, exist_ok=True)

    for file in os.listdir(RAW_FOLDER):

        path = os.path.join(RAW_FOLDER, file)

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

    with open(OUTPUT, "w") as f:
        json.dump(documents, f, indent=2)

    print("Total documents created:", len(documents))


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--user_id", required=True)

    args = parser.parse_args()

    preprocess(args.user_id)