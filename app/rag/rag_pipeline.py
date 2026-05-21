import json
import logging

import faiss
import torch

from app.rag.embeddings import EmbeddingModel
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class RAGPipeline:

    def __init__(self, company_id):

        logger.info("Loading RAG system for company %s", company_id)

        self.embedding_model = EmbeddingModel()

        vector_path = "data/users/LabData/vector_store"

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

        logger.info("Loaded %d documents for retrieval", len(self.documents))


    def retrieve(self, query):

        results = self.retriever.retrieve(query, k=5)

        return results
    
def get_rag_context(query, company_id):

    rag = RAGPipeline(company_id)

    docs = rag.retrieve(query)

    context = "\n".join(docs)

    return context