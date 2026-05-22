from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from backend.database import Base


class PasswordResetToken(Base):
    """A single-use, short-lived password-reset token. Only the SHA-256 hash
    of the token is stored, so a database leak does not expose usable tokens."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
