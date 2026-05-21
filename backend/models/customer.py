from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from backend.database import Base


class Customer(Base):
    """An end person who emails a Company for support. Scoped to one Company —
    the same email address under two Companies is two distinct Customers."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_customers_company_email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer, ForeignKey("companies.id"), nullable=False, index=True
    )
    email = Column(String, nullable=False)
    name = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
