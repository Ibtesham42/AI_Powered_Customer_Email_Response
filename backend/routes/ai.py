from fastapi import APIRouter, Depends
from backend.auth.dependencies import get_current_user

from app.llm.prompt_builder import build_email_prompt
from app.llm.llm_client import LLMClient
from app.rag.rag_pipeline import RAGPipeline
from backend.database import get_db
from backend.models.email import Email
from sqlalchemy.orm import Session

router = APIRouter()

llm = LLMClient()


@router.post("/generate-reply")
def generate_reply(email_id: int, email_text: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    rag = RAGPipeline(user_id="demo_user")

    context = rag.retrieve(email_text)

    prompt = build_email_prompt(email_text, context)

    response = llm.generate(prompt)

    # SAVE IN DB
    email = db.query(Email).filter(Email.id == email_id).first()

    email.ai_reply = response
    email.status = "replied"

    db.commit()

    return {"reply": response}