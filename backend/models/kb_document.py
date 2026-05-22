from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from backend.database import Base
from backend.models.enums import KbDocStatus


class KbDocument(Base):
    """An uploaded knowledge-base source — a file, a URL, or an FAQ entry.

    Each KbDocument is chunked into ``KbChunk`` rows for retrieval. Scoped to
    one Company; the knowledge base is strictly per-tenant (ADR-0003).
    """

    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    filename = Column(String)
    doc_type = Column(String, nullable=False)
    source_uri = Column(String)  # stored file path or URL
    status = Column(String, nullable=False, default=KbDocStatus.PENDING)
    error = Column(String, nullable=True)  # failure detail when status=error

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    indexed_at = Column(DateTime(timezone=True), nullable=True)
