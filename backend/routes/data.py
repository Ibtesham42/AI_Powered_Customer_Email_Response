from fastapi import APIRouter, UploadFile, File, Depends
import os
import shutil

from backend.auth.dependencies import get_current_user
import sys

router = APIRouter()

import subprocess

@router.post("/upload")
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):

    company = str(user["company_id"])

    folder = f"data/users/{company}/raw"
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

   

    subprocess.run([sys.executable, "scripts/build_rag.py", "--user_id", company])
    subprocess.run([sys.executable, "app/rag/preprocess.py", "--user_id", company])

    return {"message": "File uploaded and RAG updated"}