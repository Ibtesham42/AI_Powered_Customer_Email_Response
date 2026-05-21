
from fastapi import APIRouter, Depends
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.email.email_queue import add_to_queue
from app.email.email_sender import EmailSender
from app.utils.config import Config
from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.email import Email

router = APIRouter()
logger = get_logger(__name__)


# ---------------- GET ALL ----------------
@router.get("/all")
def get_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):

    return db.query(Email).filter(
        Email.company_id == user["company_id"]
    ).order_by(Email.id.desc()).all()


# ---------------- CREATE ----------------
@router.post("/create")
def create_email(subject: str, body: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = Email(
        subject=subject,
        body=body,
        company_id=user["company_id"],
        status="NEW"
    )

    db.add(email)
    db.commit()
    db.refresh(email)

    # queue for AI
    add_to_queue(email.id, user["company_id"])

    return {"message": "Email created", "id": email.id}


# ---------------- GENERATE AI ----------------
@router.post("/generate-reply/{email_id}")
def generate_reply(email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    from backend.services.ai_service import generate_email_reply

    result = generate_email_reply(
        email.body,
        user["company_id"],
        db=db,
        thread_id=email.thread_id
    )

    # ✅ FIXED (no dict issue)
    email.ai_reply = result["reply"]
    email.confidence = result["confidence"]
    email.status = "AI_GENERATED"

    db.commit()

    return result


# ---------------- HUMAN EDIT ----------------
@router.put("/update-reply")
def update_reply(email_id: int, new_reply: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    email.final_reply = new_reply
    email.status = "HUMAN_REVIEWED"

    db.commit()

    return {"message": "Reply updated"}


# ---------------- SEND ----------------
@router.post("/send/{email_id}")
def send_email(email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    if email.status == "SENT":
        return {"message": "Already sent"}

    # ---------- SAFETY ----------
    to_email = email.sender or Config.EMAIL_USER

    if not to_email:
        return {"error": "No recipient email"}

    reply_text = email.final_reply or email.ai_reply

    if not reply_text:
        return {"error": "No reply content"}

    # ---------- SMTP ----------
    sender = EmailSender(
        Config.EMAIL_USER,
        Config.EMAIL_PASS
    )

    logger.info("Sending reply for email %s to %s", email.id, to_email)
    logger.debug("Original message_id: %s", email.message_id)

    sender.send_email(
        to_email=to_email,
        subject=f"Re: {email.subject}",
        body=reply_text,
        message_id=email.message_id
    )

    # ---------- UPDATE ----------
    email.status = "SENT"
    db.commit()

    return {"message": "Email sent successfully"}


# ---------------- TODO ----------------
@router.get("/todo")
def get_todo(user=Depends(get_current_user), db: Session = Depends(get_db)):

    return db.query(Email).filter(
        Email.company_id == user["company_id"],
        Email.status == "AI_GENERATED",
        
    ).order_by(
        asc(Email.confidence)  
    ).all()

# ---------------- STATS ----------------
@router.get("/stats")
def get_stats(user=Depends(get_current_user), db: Session = Depends(get_db)):

    base = db.query(Email).filter(
        Email.company_id == user["company_id"]
    )

    return {
        "total_emails": base.count(),
        "new": base.filter(Email.status == "NEW").count(),
        "ai_generated": base.filter(Email.status == "AI_GENERATED").count(),
        "reviewed": base.filter(Email.status == "HUMAN_REVIEWED").count(),
        "sent": base.filter(Email.status == "SENT").count(),
    }


@router.get("/thread/{thread_id}")
def get_thread(thread_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    emails = db.query(Email).filter(
        Email.thread_id == thread_id,
        Email.company_id == user["company_id"]
    ).order_by(Email.id.asc()).all()

    return emails


@router.post("/assign")
def assign_email(email_id: int, agent_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    email.assigned_to = agent_id
    db.commit()

    return {"message": f"Assigned to agent {agent_id}"}
