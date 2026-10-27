from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Transaction
from app.summary import month_bounds, monthly_summary


def db_with(*txs):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(txs)
    db.commit()
    return db


def tx(ref, direction, amount, when, category="Transfers", fee=0):
    return Transaction(
        provider="mtn", kind="send", direction=direction, amount=amount, fee=fee,
        category=category, occurred_at=when, reference=ref, raw_message="x",
    )


def test_month_bounds_december_rolls_over_year():
    assert month_bounds("2026-12") == (datetime(2026, 12, 1), datetime(2027, 1, 1))


@pytest.mark.parametrize("bad", ["2026-13", "2026-1", "October", "", "2026/10"])
def test_month_bounds_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        month_bounds(bad)


def test_summary_totals_and_categories():
    db = db_with(
        tx("a", "in", 100000, datetime(2026, 10, 1), "Income"),
        tx("b", "out", 30000, datetime(2026, 10, 5), "Transport", fee=500),
        tx("c", "out", 50000, datetime(2026, 10, 31, 23, 59), "Education", fee=1000),
        tx("d", "out", 99999, datetime(2026, 11, 1), "Transport"),   # next month: excluded
        tx("e", "out", 99999, datetime(2026, 9, 30, 23, 59), "Transport"),  # previous month
    )
    s = monthly_summary(db, "2026-10")
    assert s["transaction_count"] == 3
    assert s["total_income"] == 100000
    assert s["total_spent"] == 80000
    assert s["total_fees"] == 1500
    assert s["net"] == 100000 - 80000 - 1500
    assert s["spending_by_category"] == [
        {"category": "Education", "total": 50000},
        {"category": "Transport", "total": 30000},
    ]


def test_empty_month():
    s = monthly_summary(db_with(), "2026-10")
    assert s["net"] == 0 and s["spending_by_category"] == []