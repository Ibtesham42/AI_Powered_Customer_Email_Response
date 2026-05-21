from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB

from backend.database import Base


class AuditLog(Base):
    """A security-relevant action record (login, mailbox connect, email send,
    etc.). Written in Phase 2 chunk 4 onward."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    entity_type = Column(String)
    entity_id = Column(Integer)
    meta = Column("metadata", JSONB)  # DB column "metadata"; "meta" avoids the
    # reserved SQLAlchemy declarative attribute name.
    ip_address = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
