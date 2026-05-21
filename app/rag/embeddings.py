import logging

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