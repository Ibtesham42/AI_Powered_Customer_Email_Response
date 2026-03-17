import faiss
import numpy as np
import json
from pathlib import Path


class VectorStore:

    def __init__(self):

        self.index = None
        self.documents = []

    def build(self, embeddings, docs):

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dimension)

        self.index.add(embeddings.cpu().numpy())

        self.documents = docs

        Path("vector_store").mkdir(exist_ok=True)

        faiss.write_index(self.index, "vector_store/faiss_index")

        with open("vector_store/docs.json", "w") as f:
            json.dump(docs, f)

        print("Vector store saved")

    def load(self):

        self.index = faiss.read_index("vector_store/faiss_index")

        with open("vector_store/docs.json") as f:
            self.documents = json.load(f)