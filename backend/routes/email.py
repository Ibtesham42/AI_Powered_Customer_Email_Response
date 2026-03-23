from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.email import Email
from backend.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/all")
def get_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):

    return db.query(Email).filter(
        Email.company_id == user["company_id"]
    ).all()


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.email import Email
from backend.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/all")
def get_emails(user=Depends(get_current_user), db: Session = Depends(get_db)):

    return db.query(Email).filter(
        Email.company_id == user["company_id"]
    ).all()


@router.post("/create")
def create_email(subject: str, body: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = Email(
        subject=subject,
        body=body,
        company_id=user["company_id"]  #  KEY LINE
    )

    db.add(email)
    db.commit()
    db.refresh(email)

    return {"message": "Email created"}

@router.put("/update-reply")
def update_reply(email_id: int, new_reply: str, db: Session = Depends(get_db)):

    email = db.query(Email).filter(Email.id == email_id).first()

    email.ai_reply = new_reply
    email.status = "replied"

    db.commit()

    return {"message": "Reply updated"}

@router.post("/send")
def send_email(email_id: int, db: Session = Depends(get_db)):

    email = db.query(Email).filter(Email.id == email_id).first()

    #  future: integrate SMTP / SendGrid
    print("Sending email:", email.ai_reply)

    return {"message": "Email sent successfully"}

@router.put("/update-reply")
def update_reply(email_id: int, new_reply: str, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    email.ai_reply = new_reply
    email.status = "replied"

    db.commit()

    return {"message": "Reply updated"}

@router.post("/send")
def send_email(email_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):

    email = db.query(Email).filter(
        Email.id == email_id,
        Email.company_id == user["company_id"]
    ).first()

    if not email:
        return {"error": "Email not found"}

    print("Sending email:", email.ai_reply)

    return {"message": "Email sent successfully"}