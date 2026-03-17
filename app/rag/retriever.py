import torch
from sentence_transformers import util


class Retriever:

    def __init__(self, embedding_model, embeddings, documents):

        self.embedding_model = embedding_model
        self.embeddings = embeddings
        self.documents = documents

        # detect device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # move embeddings to same device
        self.embeddings = self.embeddings.to(self.device)


    def retrieve(self, query, k=5):

        query_embedding = self.embedding_model.model.encode(
            query,
            convert_to_tensor=True
        ).to(self.device)

        scores = util.dot_score(query_embedding, self.embeddings)[0]

        top_results = torch.topk(scores, k)

        results = []

        for idx in top_results.indices:
            results.append(self.documents[idx]["text"])

        return results