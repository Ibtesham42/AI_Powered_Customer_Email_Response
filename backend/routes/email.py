
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.email import Email
from backend.auth.dependencies import get_current_user

from app.email.email_queue import add_to_queue
from app.email.email_sender import EmailSender
from app.utils.config import Config

router = APIRouter()


# =========================
# GET ALL EMAILS
# =========================
@router.get("/all")
def get_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):

    return db.query(Email).filter(
        Email.company_id == user["company_id"]
    ).all()


# =========================
# CREATE EMAIL (Manual/Test)
# =========================
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

    # add to queue for AI processing
    add_to_queue(email.id, user["company_id"])

    return {"message": "Email created", "id": email.id}


# =========================
# GENERATE AI REPLY
# =========================
@router.post("/generate-reply/{email_id}")
def generate_reply(email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    from backend.services.ai_service import generate_email_reply

    ai_reply = generate_email_reply(
        email.body,
        user["company_id"]
    )

    email.ai_reply = ai_reply
    email.status = "AI_GENERATED"

    db.commit()

    return {"ai_reply": ai_reply}


# =========================
# HUMAN EDIT
# =========================
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


# =========================
# SEND EMAIL (SMTP)
# =========================
@router.post("/send/{email_id}")
def send_email(email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    # prevent double send
    if email.status == "SENT":
        return {"message": "Already sent"}

    # init sender
    sender = EmailSender(
        Config.EMAIL_USER,
        Config.EMAIL_PASS
    )

    print("Sending to:", email.sender)

    # send email
    sender.send_email(
        to_email=email.sender,
        subject=f"Re: {email.subject}",
        body=email.final_reply or email.ai_reply
    )

    # update status
    email.status = "SENT"
    db.commit()

    return {"message": "Email sent successfully"}


# =========================
# TODO (HUMAN REVIEW QUEUE)
# =========================
@router.get("/todo")
def get_todo(user=Depends(get_current_user), db: Session = Depends(get_db)):

    emails = db.query(Email).filter(
        Email.company_id == user["company_id"],
        Email.status == "AI_GENERATED"
    ).all()

    return emails


# =========================
# DASHBOARD STATS
# =========================
@router.get("/stats")
def get_stats(user=Depends(get_current_user), db: Session = Depends(get_db)):

    base = db.query(Email).filter(Email.company_id == user["company_id"])

    return {
        "total_emails": base.count(),
        "replied": base.filter(Email.status == "SENT").count(),
        "pending": base.filter(Email.status == "AI_GENERATED").count(),
        "reviewed": base.filter(Email.status == "HUMAN_REVIEWED").count(),
    }

