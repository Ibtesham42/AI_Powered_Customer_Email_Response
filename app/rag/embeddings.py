import logging
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:

    def __init__(self):

        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5",
            device=device
        )

        logger.info("Embedding model running on %s", device)

    def embed(self, texts):

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=True
        )

        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed texts for storage in pgvector — returns plain float lists."""
        vectors = self.model.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for retrieval — returns a plain list."""
        vector = self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    """Process-wide singleton. Loading the SentenceTransformer is expensive, so
    it must happen once per process — not once per request (the old bug)."""
    return EmbeddingModel()