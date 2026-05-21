from sqlalchemy import Column, Integer, String, ForeignKey
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))
    role = Column(String, default="agent")