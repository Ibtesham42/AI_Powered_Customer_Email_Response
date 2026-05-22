import os
import shutil
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
from backend.auth.dependencies import get_current_user, require_owner
from backend.database import get_db
from backend.logging_config import get_logger
from backend.serializers import kb_document_dict
from backend.services import audit_service, kb_service

router = APIRouter()
logger = get_logger(__name__)


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

    folder = f"data/users/{company_id}/raw"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
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


@router.get("/documents")
def list_documents(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the Company's knowledge-base documents and their indexing status."""
    documents = kb_service.list_documents(db, user["company_id"])
    return [kb_document_dict(d) for d in documents]
