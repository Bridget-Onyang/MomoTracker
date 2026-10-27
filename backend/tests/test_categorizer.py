import pytest

from app.categorizer import categorize


@pytest.mark.parametrize(
    "kind, direction, name, expected",
    [
        ("withdraw", "out", "KAMYA STORES", "Cash Withdrawal"),
        ("airtime", "out", None, "Airtime & Data"),
        ("receive", "in", "JANE NAKATO", "Income"),
        ("deposit", "in", None, "Income"),
        ("payment", "out", "UMEME PREPAID", "Utilities"),
        ("payment", "out", "SafeBoda Ltd", "Transport"),
        ("payment", "out", "UCU Tuition", "Education"),
        ("send", "out", "JOHN DOE", "Transfers"),
        ("payment", "out", "RANDOM SHOP", "Uncategorized"),
        ("payment", "out", None, "Uncategorized"),
    ],
)
def test_categorize(kind, direction, name, expected):
    assert categorize(kind, direction, name) == expected


def test_kind_beats_keyword():
    # A withdrawal at an agent whose name contains "school" is still a withdrawal.
    assert categorize("withdraw", "out", "SCHOOL CANTEEN AGENT") == "Cash Withdrawal"