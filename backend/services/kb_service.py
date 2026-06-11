"""Knowledge-base ingestion — extract, chunk, embed, store as KbChunks.

Per-Company: every KbDocument and KbChunk carries a ``company_id``. Ingestion
runs in-process (no subprocess); the heavy embedding model is a process-wide
singleton (see ``app.rag.embeddings.get_embedding_model``).

A KbDocument's source is one of three kinds, distinguished by ``doc_type``:
an uploaded file, an FAQ entry (stored as a text file), or a URL.
"""

import os
import secrets
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.rag.chunking import chunk_documents
from app.rag.embeddings import get_embedding_model
from app.rag.extract import extract_text, fetch_url_text
from backend.database import SessionLocal
from backend.logging_config import get_logger
from backend.models.enums import KbDocStatus, KbDocType
from backend.models.kb_chunk import KbChunk
from backend.models.kb_document import KbDocument

logger = get_logger(__name__)

_EXT_TO_DOC_TYPE = {
    ".pdf": KbDocType.PDF,
    ".docx": KbDocType.DOCX,
    ".csv": KbDocType.CSV,
    ".txt": KbDocType.TXT,
    ".json": KbDocType.JSON,
}


def create_document(
    db: Session,
    company_id: int,
    *,
    filename: str,
    source_uri: str,
    doc_type: str | None = None,
) -> KbDocument:
    """Register a knowledge-base source as a `pending` KbDocument.

    ``doc_type`` is derived from the filename extension when not given (file
    uploads); URL and FAQ callers pass it explicitly.
    """
    if doc_type is None:
        ext = Path(filename).suffix.lower()
        doc_type = _EXT_TO_DOC_TYPE.get(ext, KbDocType.TXT)
    document = KbDocument(
        company_id=company_id,
        filename=filename,
        doc_type=doc_type,
        source_uri=source_uri,
        status=KbDocStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def create_faq(
    db: Session, company_id: int, *, question: str, answer: str
) -> KbDocument:
    """Register an FAQ entry. The question + answer is written to a text file
    under the Company's raw folder, then ingested like any other source."""
    folder = f"data/users/{company_id}/raw"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"faq-{secrets.token_hex(6)}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Q: {question}\nA: {answer}\n")
    return create_document(
        db,
        company_id,
        filename=question[:120],
        source_uri=file_path,
        doc_type=KbDocType.FAQ,
    )


def list_documents(db: Session, company_id: int) -> list[KbDocument]:
    """All KB documents for a Company, newest first."""
    return (
        db.query(KbDocument)
        .filter(KbDocument.company_id == company_id)
        .order_by(KbDocument.id.desc())
        .all()
    )


def count_documents(db: Session, company_id: int) -> int:
    """How many KB documents a Company has — feeds the per-Company quota."""
    return db.query(KbDocument).filter(KbDocument.company_id == company_id).count()


def _load_document_text(document: KbDocument) -> str:
    """Get the raw text of a KbDocument from its source.

    Files and FAQs are read from disk; URLs are fetched.
    """
    if document.doc_type == KbDocType.URL:
        return fetch_url_text(document.source_uri)
    return extract_text(document.source_uri)


def ingest_document(document_id: int) -> None:
    """Load text -> chunk -> embed -> store the chunks for one KbDocument.

    Designed to run as a background task: it opens its own DB session (the
    request's session is already closed) and never raises — failure is
    recorded on the KbDocument's ``status`` / ``error``.
    """
    db = SessionLocal()
    try:
        document = db.query(KbDocument).filter(KbDocument.id == document_id).first()
        if document is None:
            logger.error("KbDocument %s not found — skipping ingest", document_id)
            return
        try:
            document.status = KbDocStatus.PROCESSING
            db.commit()

            text = _load_document_text(document)
            chunks = chunk_documents([{"text": text, "metadata": {}}])
            contents = [c["text"] for c in chunks]
            if not contents:
                raise ValueError("no text could be extracted from the source")

            vectors = get_embedding_model().embed_documents(contents)

            # Replace any prior chunks so a re-ingest is idempotent.
            db.query(KbChunk).filter(KbChunk.document_id == document.id).delete()
            for index, (content, vector) in enumerate(
                zip(contents, vectors, strict=True)
            ):
                db.add(
                    KbChunk(
                        company_id=document.company_id,
                        document_id=document.id,
                        chunk_index=index,
                        content=content,
                        embedding=vector,
                    )
                )

            document.status = KbDocStatus.INDEXED
            document.indexed_at = func.now()
            document.error = None
            db.commit()
            logger.info("Indexed KbDocument %s — %d chunks", document.id, len(contents))
        except Exception as exc:
            db.rollback()
            _mark_error(db, document_id, str(exc))
            logger.exception("Ingesting KbDocument %s failed", document_id)
    finally:
        db.close()


def _mark_error(db: Session, document_id: int, message: str) -> None:
    """Record an ingestion failure on the KbDocument."""
    document = db.query(KbDocument).filter(KbDocument.id == document_id).first()
    if document is None:
        return
    document.status = KbDocStatus.ERROR
    document.error = message[:500]
    db.commit()
