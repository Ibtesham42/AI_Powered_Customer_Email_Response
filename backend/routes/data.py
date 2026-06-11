import os
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.rag.extract import SUPPORTED_EXTENSIONS
from app.rag.url_guard import UnsafeUrlError, validate_public_url
from backend.auth.dependencies import get_current_user, require_owner
from backend.config import settings
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.enums import KbDocType
from backend.models.schemas import FaqIngestRequest, UrlIngestRequest
from backend.serializers import kb_document_dict
from backend.services import audit_service, kb_service

router = APIRouter()
logger = get_logger(__name__)


def _enforce_document_quota(db: Session, company_id: int) -> None:
    """409 when the Company is at its KB-document quota (B-6).

    Applies to every ingestion route (file/url/faq) — bounds disk, embedding
    work and pgvector growth per tenant.
    """
    if kb_service.count_documents(db, company_id) >= settings.KB_MAX_DOCS_PER_COMPANY:
        raise HTTPException(
            status_code=409,
            detail=(
                "Knowledge-base document limit reached "
                f"({settings.KB_MAX_DOCS_PER_COMPANY}). Delete unused documents "
                "or contact support to raise the limit."
            ),
        )


def _save_upload_capped(upload: UploadFile, file_path: str) -> None:
    """Stream the upload to disk, aborting with 413 past the size cap.

    Chunked so an oversized body is rejected after cap+1 bytes, not after
    buffering the whole file; the partial file is removed on rejection.
    """
    max_bytes = settings.KB_MAX_FILE_MB * 1024 * 1024
    written = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := upload.file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds the {settings.KB_MAX_FILE_MB} MB "
                            "knowledge-base upload limit."
                        ),
                    )
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise


@router.post("/upload")
def upload_file(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Upload a knowledge-base file (Owner-only).

    The file is saved and registered as a KbDocument, then extracted, chunked
    and embedded into pgvector by an in-process background task — the response
    returns immediately with the document's `pending` status.
    """
    company_id = user["company_id"]
    filename = os.path.basename(file.filename or "")
    if not filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type {ext!r}. Supported: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    _enforce_document_quota(db, company_id)

    folder = f"data/users/{company_id}/raw"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    _save_upload_capped(file, file_path)
    logger.info("KB file saved: %s", file_path)

    document = kb_service.create_document(
        db, company_id, filename=filename, source_uri=file_path
    )
    background_tasks.add_task(kb_service.ingest_document, document.id)

    audit_service.record(
        db,
        action="kb_document_uploaded",
        request=request,
        company_id=company_id,
        user_id=user["id"],
        entity_type="kb_document",
        entity_id=document.id,
        metadata={"filename": filename},
    )

    return {
        "message": "File uploaded; indexing started.",
        "document": kb_document_dict(document),
    }


@router.post("/url")
def ingest_url(
    payload: UrlIngestRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user=Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Ingest a web page into the knowledge base (Owner-only). The page is
    fetched, extracted, chunked and embedded by a background task."""
    company_id = user["company_id"]
    url = str(payload.url)

    # SSRF guard: reject internal/metadata targets before doing any work. The
    # background fetch re-validates (incl. each redirect hop) as defence in depth.
    try:
        validate_public_url(url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _enforce_document_quota(db, company_id)

    document = kb_service.create_document(
        db,
        company_id,
        filename=url,
        source_uri=url,
        doc_type=KbDocType.URL,
    )
    background_tasks.add_task(kb_service.ingest_document, document.id)

    audit_service.record(
        db,
        action="kb_document_uploaded",
        request=request,
        company_id=company_id,
        user_id=user["id"],
        entity_type="kb_document",
        entity_id=document.id,
        metadata={"url": url},
    )
    return {
        "message": "URL submitted; indexing started.",
        "document": kb_document_dict(document),
    }


@router.post("/faq")
def ingest_faq(
    payload: FaqIngestRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user=Depends(require_owner),
    db: Session = Depends(get_db),
):
    """Add an FAQ entry to the knowledge base (Owner-only)."""
    company_id = user["company_id"]
    _enforce_document_quota(db, company_id)

    document = kb_service.create_faq(
        db, company_id, question=payload.question, answer=payload.answer
    )
    background_tasks.add_task(kb_service.ingest_document, document.id)

    audit_service.record(
        db,
        action="kb_document_uploaded",
        request=request,
        company_id=company_id,
        user_id=user["id"],
        entity_type="kb_document",
        entity_id=document.id,
        metadata={"faq_question": payload.question[:100]},
    )
    return {
        "message": "FAQ added; indexing started.",
        "document": kb_document_dict(document),
    }


@router.get("/documents")
def list_documents(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the Company's knowledge-base documents and their indexing status."""
    documents = kb_service.list_documents(db, user["company_id"])
    return [kb_document_dict(d) for d in documents]
