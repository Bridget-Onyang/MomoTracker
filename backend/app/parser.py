"""Parse MTN MoMo / Airtel Money confirmation SMS text into structured data.

IMPORTANT: the message templates below are *representative*, written from
general knowledge of the services. Telecoms change their wording. Before
trusting this in real use, paste real (anonymised) messages into
tests/test_parser.py and adjust the patterns. The design makes that easy:
add a regex to MAIN_PATTERNS and a test.

Design rules:
  * A message either parses completely (amount, date, reference) or it is
    reported as a failure with a reason. We never guess a date or amount,
    because silently wrong numbers are worse than a visible failure.
  * Fee, balance and counterparty are optional extras.
"""
import re
from dataclasses import dataclass
from datetime import datetime

_CUR = r"(?:UGX|USh|Ush|Shs)\.?"
_AMT = r"(?P<amount>\d[\d,]*(?:\.\d+)?)"
_NAME = r"(?P<name>[A-Za-z][A-Za-z .'\-]*?)"
_PHONE = r"(?P<phone>\+?\d{9,13})"

# (kind, direction, compiled regex). First match wins, so order matters.
MAIN_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (kind, direction, re.compile(pattern, re.IGNORECASE | re.DOTALL))
    for kind, direction, pattern in [
        ("send", "out", rf"\bsent\s+{_CUR}\s?{_AMT}\s+to\s+{_NAME}\s*(?:\(?{_PHONE}\)?)?(?=\s+on\b|\s*\.|\s*,|$)"),
        ("receive", "in", rf"\breceived\s+{_CUR}\s?{_AMT}\s+from\s+{_NAME}\s*(?:\(?{_PHONE}\)?)?(?=\s+on\b|\s*\.|\s*,|$)"),
        ("withdraw", "out", rf"\bwithdraw(?:n|al)?\b.*?{_CUR}\s?{_AMT}(?:.*?\bagent\s+{_NAME}(?=\s+on\b|\s*\.|\s*,|$))?"),
        ("deposit", "in", rf"\b(?:deposit(?:ed)?|cash\s*in)\b.*?{_CUR}\s?{_AMT}(?:.*?\bfrom\s+{_NAME}(?=\s+on\b|\s*\.|\s*,|$))?"),
        ("airtime", "out", rf"\bbought\s+{_CUR}\s?{_AMT}\s+(?:of\s+)?(?:airtime|data)"),
        ("airtime", "out", rf"\b(?:airtime|data\s+bundle)\b.*?{_CUR}\s?{_AMT}"),
        ("payment", "out", rf"\b(?:paid|payment\s+of)\s+{_CUR}\s?{_AMT}\s+to\s+{_NAME}(?=\s+on\b|\s*\.|\s*,|$)"),
    ]
]

_FEE = re.compile(rf"\bfee(?:\s+of)?\s*:?\s*{_CUR}?\s?(\d[\d,]*)", re.IGNORECASE)
_BALANCE = re.compile(rf"\b(?:new\s+)?bal(?:ance)?(?:\s+is)?\s*:?\s*{_CUR}?\s?(\d[\d,]*)", re.IGNORECASE)
_REF = re.compile(r"\b(?:transaction\s+id|txn\s*id|tid|ref(?:erence)?(?:\s+no)?)\s*[:#]?\s*([A-Za-z0-9]{6,})", re.IGNORECASE)
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})[ T]+(\d{1,2}:\d{2}(?::\d{2})?)")


@dataclass
class ParsedTransaction:
    provider: str
    kind: str
    direction: str
    amount: int
    fee: int
    balance_after: int | None
    counterparty_name: str | None
    counterparty_phone: str | None
    occurred_at: datetime
    reference: str
    raw_message: str


class ParseError(ValueError):
    """Raised when a message cannot be parsed safely."""


def _to_int(text: str) -> int:
    # UGX amounts are whole shillings; drop commas and any ".00".
    return int(float(text.replace(",", "")))


def detect_provider(message: str, hint: str | None = None) -> str:
    low = message.lower()
    if "airtel" in low:
        return "airtel"
    if "mtn" in low or "momo" in low:
        return "mtn"
    if hint in ("mtn", "airtel"):
        return hint
    raise ParseError("cannot tell provider (MTN or Airtel); pick one when importing")


def _parse_date(message: str) -> datetime:
    m = _DATE.search(message)
    if not m:
        raise ParseError("no date/time found")
    day, clock = m.group(1), m.group(2)
    if len(clock) <= 5:
        clock += ":00"
    fmt = "%Y-%m-%d %H:%M:%S" if "-" in day else "%d/%m/%Y %H:%M:%S"
    try:
        return datetime.strptime(f"{day} {clock}", fmt)
    except ValueError as exc:
        raise ParseError(f"invalid date: {exc}") from exc


def parse_message(message: str, provider_hint: str | None = None) -> ParsedTransaction:
    """Parse one SMS. Raises ParseError with a human-readable reason."""
    text = " ".join(message.split())  # collapse newlines / repeated spaces
    if not text:
        raise ParseError("empty message")

    provider = detect_provider(text, provider_hint)

    for kind, direction, pattern in MAIN_PATTERNS:
        m = pattern.search(text)
        if m:
            break
    else:
        raise ParseError("message format not recognised")

    groups = m.groupdict()
    ref = _REF.search(text)
    if not ref:
        raise ParseError("no transaction ID found")
    fee = _FEE.search(text)
    bal = _BALANCE.search(text)
    name = groups.get("name")

    return ParsedTransaction(
        provider=provider,
        kind=kind,
        direction=direction,
        amount=_to_int(groups["amount"]),
        fee=_to_int(fee.group(1)) if fee else 0,
        balance_after=_to_int(bal.group(1)) if bal else None,
        counterparty_name=name.strip().upper() if name else None,
        counterparty_phone=groups.get("phone"),
        occurred_at=_parse_date(text),
        reference=ref.group(1),
        raw_message=message.strip(),
    )


def split_messages(blob: str) -> list[str]:
    """Split pasted text / file contents into individual messages.

    Messages are separated by blank lines. If there are no blank lines but
    several lines, each non-empty line is treated as one message.
    """
    blob = blob.replace("\r\n", "\n").strip()
    chunks = [c.strip() for c in re.split(r"\n\s*\n", blob) if c.strip()]
    if len(chunks) == 1 and "\n" in chunks[0]:
        chunks = [ln.strip() for ln in chunks[0].split("\n") if ln.strip()]
    return chunks