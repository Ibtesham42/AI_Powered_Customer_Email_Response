from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
from backend.models.company import Company   #  ADD THIS


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)

    sender = Column(String)
    subject = Column(String)
    body = Column(String)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company")

    status = Column(String, default="NEW")

    ai_reply = Column(String, nullable=True)
    final_reply = Column(String, nullable=True)