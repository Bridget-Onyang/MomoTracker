"""Rule-based categorisation. Deliberately simple and transparent.

Order of decisions:
  1. Transaction kind (withdraw, airtime, money in) decides first.
  2. Keywords in the counterparty name decide next.
  3. Otherwise a plain send is "Transfers", anything else "Uncategorized".
Users can override any category later through the API.
"""

KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Utilities", ("umeme", "nwsc", "yaka", "water", "electricity", "dstv", "gotv", "startimes")),
    ("Transport", ("safeboda", "uber", "bolt", "faras", "fuel", "shell", "total energies", "stabex")),
    ("Food & Groceries", ("kfc", "java", "cafe", "restaurant", "supermarket", "carrefour", "quality", "food")),
    ("Education", ("school", "university", "tuition", "college", "academy", "ucu")),
    ("Health", ("pharmacy", "clinic", "hospital", "medical")),
]


def categorize(kind: str, direction: str, counterparty_name: str | None) -> str:
    if kind == "withdraw":
        return "Cash Withdrawal"
    if kind == "airtime":
        return "Airtime & Data"
    if direction == "in":
        return "Income"

    name = (counterparty_name or "").lower()
    for category, keywords in KEYWORD_RULES:
        if any(word in name for word in keywords):
            return category

    return "Transfers" if kind == "send" else "Uncategorized"