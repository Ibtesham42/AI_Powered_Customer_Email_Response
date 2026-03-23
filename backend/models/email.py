from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from backend.database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    body = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))

    #  NEW FIELDS
    ai_reply = Column(String, nullable=True)
    status = Column(String, default="pending")  
    # pending / replied