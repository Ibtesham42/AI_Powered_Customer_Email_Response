from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password_hash = Column(String)
    company_id = Column(Integer, ForeignKey("companies.id"))
    # Role within the Company: "owner" (created it) or "agent".
    role = Column(String, default="agent")
    # Bumped to invalidate every outstanding access token for this user (a
    # "sign out everywhere" / post-reset kill switch). The access-token JWT
    # carries this value; get_current_user rejects a token whose version differs.
    token_version = Column(Integer, nullable=False, default=1, server_default="1")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
