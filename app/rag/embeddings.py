import logging
import os
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def resolve_device() -> str:
    """The device the embedding model runs on.

    ``EMBEDDING_DEVICE`` (e.g. ``cpu`` or ``cuda``) overrides the
    cuda-if-available default. The override exists because the api and the
    worker BOTH load this model (KB ingestion embeds in the api process,
    retrieval in the worker): two processes creating CUDA contexts at the same
    moment on a small GPU (e.g. a 4 GB laptop card) crash natively, without a
    Python traceback. Single-box deploys should pin ``EMBEDDING_DEVICE=cpu``.
    """
    override = os.getenv("EMBEDDING_DEVICE", "").strip().lower()
    if override:
        return override
    return "cuda" if torch.cuda.is_available() else "cpu"


class EmbeddingModel:

    def __init__(self):

        device = resolve_device()

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