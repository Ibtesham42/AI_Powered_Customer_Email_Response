from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    func,
)

from backend.database import Base

# Embedding dimension of BAAI/bge-base-en-v1.5 — the column width must match
# the model that produces the vectors.
EMBEDDING_DIM = 768


class KbChunk(Base):
    """A chunk of a KbDocument plus its embedding — the RAG retrieval target.

    Retrieval always filters ``company_id`` first (tenant isolation), then
    orders by vector distance.
    """

    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    chunk_index = Column(Integer, nullable=False)  # order within the document
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
