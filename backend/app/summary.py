"""Monthly summary calculations (pure functions, easy to test)."""
import re
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Transaction

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def month_bounds(month: str) -> tuple[datetime, datetime]:
    """'2026-10' -> (2026-10-01 00:00, 2026-11-01 00:00)."""
    if not _MONTH.match(month):
        raise ValueError("month must look like YYYY-MM, e.g. 2026-10")
    year, mon = int(month[:4]), int(month[5:])
    start = datetime(year, mon, 1)
    end = datetime(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)
    return start, end


def monthly_summary(db: Session, month: str) -> dict:
    start, end = month_bounds(month)
    rows = db.scalars(
        select(Transaction).where(Transaction.occurred_at >= start, Transaction.occurred_at < end)
    ).all()

    income = sum(t.amount for t in rows if t.direction == "in")
    spent = sum(t.amount for t in rows if t.direction == "out")
    fees = sum(t.fee for t in rows)

    by_category: dict[str, int] = defaultdict(int)
    for t in rows:
        if t.direction == "out":
            by_category[t.category] += t.amount

    return {
        "month": month,
        "transaction_count": len(rows),
        "total_income": income,
        "total_spent": spent,
        "total_fees": fees,
        # Fees are real money leaving the wallet, so they count against net.
        "net": income - spent - fees,
        "spending_by_category": [
            {"category": c, "total": v}
            for c, v in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)
        ],
    }