"""Retrieval-Augmented Generation — per-Company knowledge-base retrieval.

The knowledge base lives in `kb_chunks` (pgvector). Retrieval embeds the query
and returns the nearest chunks for *one* Company: tenant isolation is the
`company_id` filter, exactly like every other query. This replaces the legacy
FAISS path (`app/rag/rag_pipeline.py`), which shared a single hardcoded index
across all tenants.
"""

from sqlalchemy.orm import Session

from app.rag.embeddings import get_embedding_model
from backend.logging_config import get_logger
from backend.models.kb_chunk import KbChunk

logger = get_logger(__name__)

DEFAULT_TOP_K = 5


def retrieve_chunks(
    db: Session, query: str, company_id: int, k: int = DEFAULT_TOP_K
) -> list[KbChunk]:
    """The ``k`` nearest knowledge-base chunks for a Company, by cosine
    distance. Scoped strictly to ``company_id``."""
    query_vector = get_embedding_model().embed_query(query)
    return (
        db.query(KbChunk)
        .filter(KbChunk.company_id == company_id)
        .order_by(KbChunk.embedding.cosine_distance(query_vector))
        .limit(k)
        .all()
    )


def get_rag_context(
    db: Session, query: str, company_id: int, k: int = DEFAULT_TOP_K
) -> str:
    """Newline-joined text of the top-k retrieved chunks for a Company.

    Returns an empty string if the Company has no knowledge base yet — the
    caller (the LLM prompt) handles a missing context gracefully.
    """
    chunks = retrieve_chunks(db, query, company_id, k)
    logger.info(
        "RAG retrieved %d chunk(s) for company %s", len(chunks), company_id
    )
    return "\n".join(chunk.content for chunk in chunks)
