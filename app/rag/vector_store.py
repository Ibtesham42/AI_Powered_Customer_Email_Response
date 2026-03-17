import faiss
import json
import os
from pathlib import Path


class VectorStore:

    def __init__(self, user_id):

        self.base_path = f"data/users/{user_id}/vector_store"

        self.index_path = f"{self.base_path}/faiss_index"
        self.docs_path = f"{self.base_path}/docs.json"

        self.index = None
        self.documents = []


    def build_or_update(self, embeddings, docs):

        Path(self.base_path).mkdir(parents=True, exist_ok=True)

        embeddings_np = embeddings.cpu().numpy()

        if os.path.exists(self.index_path):

            print("Loading existing vector store...")

            self.index = faiss.read_index(self.index_path)

            with open(self.docs_path) as f:
                self.documents = json.load(f)

            self.index.add(embeddings_np)

            self.documents.extend(docs)

            print("Added", len(docs), "new documents")

        else:

            print("Creating new vector store...")

            dimension = embeddings_np.shape[1]

            self.index = faiss.IndexFlatIP(dimension)

            self.index.add(embeddings_np)

            self.documents = docs

        faiss.write_index(self.index, self.index_path)

        with open(self.docs_path, "w") as f:
            json.dump(self.documents, f)

        print("Total documents:", len(self.documents))