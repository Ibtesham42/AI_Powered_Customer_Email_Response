"""Retrieval-Augmented Generation — per-Company knowledge-base retrieval.

The knowledge base lives in `kb_chunks` (pgvector). Retrieval embeds the query
and returns the nearest chunks for *one* Company: tenant isolation is the
`company_id` filter. Each result carries its cosine distance, which feeds the
retrieval-grounded confidence score in ``ai_service``.
"""

from sqlalchemy.orm import Session

from app.rag.embeddings import get_embedding_model
from backend.logging_config import get_logger
from backend.models.kb_chunk import KbChunk

logger = get_logger(__name__)

DEFAULT_TOP_K = 5


def retrieve(
    db: Session, query: str, company_id: int, k: int = DEFAULT_TOP_K
) -> list[tuple[KbChunk, float]]:
    """The ``k`` nearest knowledge-base chunks for a Company.

    Returns ``(chunk, cosine_distance)`` pairs, nearest first. Scoped strictly
    to ``company_id``; an empty list if the Company has no knowledge base.
    """
    query_vector = get_embedding_model().embed_query(query)
    distance = KbChunk.embedding.cosine_distance(query_vector)
    rows = (
        db.query(KbChunk, distance.label("distance"))
        .filter(KbChunk.company_id == company_id)
        .order_by(distance)
        .limit(k)
        .all()
    )
    logger.info(
        "RAG retrieved %d chunk(s) for company %s", len(rows), company_id
    )
    return [(row[0], float(row[1])) for row in rows]
