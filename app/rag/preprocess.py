import pandas as pd
import json
from pathlib import Path

RAW_DATA = "data/raw/rag_customer_support_dataset_50000.csv"
OUTPUT = "data/processed/documents.json"


def preprocess():

    df = pd.read_csv(RAW_DATA)

    documents = []

    for _, row in df.iterrows():

        text = f"""
Customer ID: {row.customer_id}
Customer Email: {row.customer_email}
Order ID: {row.order_id}
Product: {row.product_name}
Order Status: {row.order_status}
Payment Status: {row.payment_status}
Invoice ID: {row.invoice_id}
Ticket ID: {row.ticket_id}

Title: {row.title}
Content: {row.content}
"""

        documents.append({
            "doc_id": int(row.doc_id),
            "text": text.strip(),
            "metadata": {
                "source": row.source,
                "customer_email": row.customer_email,
                "order_id": row.order_id
            }
        })

    Path("data/processed").mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w") as f:
        json.dump(documents, f, indent=2)

    print("Documents created:", len(documents))


if __name__ == "__main__":
    preprocess()