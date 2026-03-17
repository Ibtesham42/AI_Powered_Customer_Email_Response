from app.rag.retriever import Retriever
from app.rag.embeddings import EmbeddingModel
import json
import faiss
import torch


class RAGPipeline:

    def __init__(self):

        print("Loading RAG system...")

        self.embedding_model = EmbeddingModel()

        self.index = faiss.read_index("vector_store/faiss_index")

        with open("vector_store/docs.json") as f:
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