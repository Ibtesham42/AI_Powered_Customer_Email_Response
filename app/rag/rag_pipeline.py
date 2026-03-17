from app.rag.retriever import Retriever
from app.rag.embeddings import EmbeddingModel
import json
import faiss
import torch


class RAGPipeline:

    def __init__(self, user_id):

        print("Loading RAG system for:", user_id)

        self.embedding_model = EmbeddingModel()

        vector_path = f"data/users/{user_id}/vector_store"

        index_path = f"{vector_path}/faiss_index"
        docs_path = f"{vector_path}/docs.json"

        self.index = faiss.read_index(index_path)

        with open(docs_path) as f:
            self.documents = json.load(f)

        self.embeddings = torch.tensor(
            self.index.reconstruct_n(0, self.index.ntotal)
        )

        self.retriever = Retriever(
            self.embedding_model,
            self.embeddings,
            self.documents
        )

        print("Loaded", len(self.documents), "documents")


    def retrieve(self, query):

        results = self.retriever.retrieve(query, k=5)

        return results