from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Transaction


def make_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_tx(**overrides):
    data = dict(
        provider="mtn", kind="send", direction="out", amount=50000,
        occurred_at=datetime(2026, 10, 20, 14, 32), reference="ABC123",
        raw_message="raw",
    )
    data.update(overrides)
    return Transaction(**data)


def test_can_save_and_read_transaction():
    db = make_session()
    db.add(make_tx())
    db.commit()
    tx = db.query(Transaction).one()
    assert tx.amount == 50000
    assert tx.category == "Uncategorized"
    assert tx.fee == 0


def test_same_provider_and_reference_is_rejected():
    db = make_session()
    db.add(make_tx())
    db.commit()
    db.add(make_tx())
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_reference_on_different_provider_is_allowed():
    db = make_session()
    db.add(make_tx())
    db.add(make_tx(provider="airtel"))
    db.commit()
    assert db.query(Transaction).count() == 2