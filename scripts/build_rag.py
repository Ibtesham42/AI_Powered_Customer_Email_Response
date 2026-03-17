import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json

from app.rag.chunking import chunk_documents
from app.rag.embeddings import EmbeddingModel
from app.rag.vector_store import VectorStore
from app.utils.workspace_manager import WorkspaceManager


def build(user_id):

    workspace = WorkspaceManager(user_id)

    docs_path = workspace.processed() + "/documents.json"

    with open(docs_path) as f:
        docs = json.load(f)

    chunks = chunk_documents(docs)

    texts = [c["text"] for c in chunks]

    embedding_model = EmbeddingModel()

    embeddings = embedding_model.embed(texts)

    store = VectorStore(user_id)

    store.build_or_update(embeddings, chunks)

    print("RAG index built successfully")


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--user_id", required=True)

    args = parser.parse_args()

    build(args.user_id)