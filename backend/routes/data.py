
import os
import shutil
import subprocess
import sys

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.auth.dependencies import require_owner
from backend.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ---------------- UPLOAD + TRAIN ----------------
@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    user=Depends(require_owner),
):

    try:
        company_id = str(user["company_id"])

        # ---------- CREATE FOLDER ----------
        folder = f"data/users/{company_id}/raw"
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(folder, file.filename)

        # ---------- SAVE FILE ----------
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info("File saved: %s", file_path)

        # ---------- STEP 1: PREPROCESS ----------
        subprocess.run(
            [sys.executable, "app/rag/preprocess.py", "--user_id", company_id],
            check=True
        )

        # ---------- STEP 2: BUILD RAG ----------
        subprocess.run(
            [sys.executable, "scripts/build_rag.py", "--user_id", company_id],
            check=True
        )

        logger.info("RAG retrained for company %s", company_id)

        return {"message": "File uploaded and AI trained successfully"}

    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"RAG process failed: {e}"
        ) from e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

