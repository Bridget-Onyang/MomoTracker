"""Database models.

Money is stored as integer UGX (Uganda shillings have no minor unit in
practice). Never use floats for money.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"
    # The same SMS pasted twice must not create two rows.
    __table_args__ = (UniqueConstraint("provider", "reference", name="uq_provider_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(16))        # "mtn" | "airtel"
    kind: Mapped[str] = mapped_column(String(16))            # send, receive, payment, withdraw, deposit, airtime
    direction: Mapped[str] = mapped_column(String(3))        # "in" | "out"
    amount: Mapped[int] = mapped_column(Integer)             # UGX, always positive
    fee: Mapped[int] = mapped_column(Integer, default=0)     # UGX
    balance_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    counterparty_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    counterparty_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="Uncategorized")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    reference: Mapped[str] = mapped_column(String(40))
    raw_message: Mapped[str] = mapped_column(Text)           # kept so we can re-parse when the parser improves
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)