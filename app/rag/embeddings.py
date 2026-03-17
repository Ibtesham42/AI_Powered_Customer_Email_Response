from sentence_transformers import SentenceTransformer
import torch


class EmbeddingModel:

    def __init__(self):

        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5",
            device=device
        )

        print("Embedding model running on:", device)

    def embed(self, texts):

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            convert_to_tensor=True,
            show_progress_bar=True
        )

        return embeddings