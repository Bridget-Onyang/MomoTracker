from datetime import datetime

import pytest

from app.parser import ParseError, parse_message, split_messages

# Representative samples. Replace/extend with REAL anonymised messages.
MTN_SENT = (
    "You have sent UGX 50,000 to JOHN DOE 0772123456 on 2026-10-20 14:32:10. "
    "Fee UGX 1,000. Your new balance is UGX 120,500. Transaction ID: 12345678901. MTN MoMo"
)
MTN_RECEIVED = (
    "You have received UGX 100,000 from JANE NAKATO 0701234567 on 2026-10-21 09:05:44. "
    "Your new balance is UGX 220,500. Transaction ID: 12345678902. MTN MoMo"
)
AIRTEL_SENT = (
    "Airtel Money: Sent UGX 20,000 to MARY AKELLO 0752111222 on 22/10/2026 18:10. "
    "Fee: UGX 500. Bal: UGX 45,000. TID: AM998877665"
)
MTN_AIRTIME = (
    "MTN MoMo: You bought UGX 5,000 of airtime on 2026-10-22 08:00:00. "
    "Balance UGX 40,000. Transaction ID: 12345678903"
)
MTN_WITHDRAW = (
    "You have withdrawn UGX 200,000 from agent KAMYA STORES on 2026-10-23 12:00:00. "
    "Fee UGX 3,000. New balance UGX 17,000. Transaction ID: 12345678904. MTN MoMo"
)


def test_mtn_sent():
    tx = parse_message(MTN_SENT)
    assert tx.provider == "mtn"
    assert (tx.kind, tx.direction) == ("send", "out")
    assert tx.amount == 50000 and tx.fee == 1000 and tx.balance_after == 120500
    assert tx.counterparty_name == "JOHN DOE"
    assert tx.counterparty_phone == "0772123456"
    assert tx.occurred_at == datetime(2026, 10, 20, 14, 32, 10)
    assert tx.reference == "12345678901"


def test_mtn_received():
    tx = parse_message(MTN_RECEIVED)
    assert (tx.kind, tx.direction) == ("receive", "in")
    assert tx.amount == 100000 and tx.fee == 0
    assert tx.counterparty_name == "JANE NAKATO"


def test_airtel_sent_with_slash_date():
    tx = parse_message(AIRTEL_SENT)
    assert tx.provider == "airtel"
    assert tx.amount == 20000 and tx.fee == 500 and tx.balance_after == 45000
    assert tx.occurred_at == datetime(2026, 10, 22, 18, 10, 0)
    assert tx.reference == "AM998877665"


def test_airtime():
    tx = parse_message(MTN_AIRTIME)
    assert (tx.kind, tx.direction) == ("airtime", "out")
    assert tx.amount == 5000


def test_withdraw_with_agent_and_fee():
    tx = parse_message(MTN_WITHDRAW)
    assert (tx.kind, tx.direction) == ("withdraw", "out")
    assert tx.amount == 200000 and tx.fee == 3000
    assert tx.counterparty_name == "KAMYA STORES"


def test_provider_hint_used_when_message_has_no_brand():
    msg = "You have sent UGX 1,000 to BOB 0772000000 on 2026-10-20 10:00:00. Transaction ID: ZZ1234567"
    assert parse_message(msg, provider_hint="mtn").provider == "mtn"
    with pytest.raises(ParseError, match="provider"):
        parse_message(msg)


@pytest.mark.parametrize(
    "msg, reason",
    [
        ("", "empty"),
        ("Dear customer, enjoy 10% off data this weekend! MTN", "not recognised"),
        ("MTN: You have sent UGX 1,000 to BOB 0772000000. Transaction ID: ZZ1234567", "date"),
        ("MTN: You have sent UGX 1,000 to BOB 0772000000 on 2026-10-20 10:00:00.", "transaction ID"),
    ],
)
def test_bad_messages_fail_loudly(msg, reason):
    with pytest.raises(ParseError, match=reason):
        parse_message(msg)


def test_impossible_date_is_rejected():
    msg = "MTN: You have sent UGX 1,000 to BOB 0772000000 on 2026-13-45 10:00:00. Transaction ID: ZZ1234567"
    with pytest.raises(ParseError, match="invalid date"):
        parse_message(msg)


def test_split_by_blank_lines():
    assert split_messages(f"{MTN_SENT}\n\n{MTN_RECEIVED}\n") == [MTN_SENT, MTN_RECEIVED]


def test_split_by_lines_when_no_blank_lines():
    assert split_messages(f"{MTN_SENT}\n{MTN_RECEIVED}") == [MTN_SENT, MTN_RECEIVED]