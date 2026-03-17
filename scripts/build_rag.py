import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json

from app.rag.chunking import chunk_documents
from app.rag.embeddings import EmbeddingModel
from app.rag.vector_store import VectorStore


def build():

    with open("data/processed/documents.json") as f:
        docs = json.load(f)

    chunks = chunk_documents(docs)

    texts = [c["text"] for c in chunks]

    embedding_model = EmbeddingModel()

    embeddings = embedding_model.embed(texts)

    store = VectorStore()

    store.build(embeddings, chunks)

    print("RAG index built successfully")


if __name__ == "__main__":
    build()