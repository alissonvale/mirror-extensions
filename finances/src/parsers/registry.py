"""Plug-in registry for statement parsers.

Two surfaces:

  parse_bank_statement(content, format=None) -> StatementData
  parse_credit_card_statement(content, format=None) -> CreditCardStatementData

When ``format`` is omitted, each surface auto-detects from cheap
signatures (OFX header, ``MASTERCARD`` / ``VISA`` line, etc.). Auto-
detection is intentionally conservative; it raises if it cannot make
up its mind so the user is told exactly which ``--format`` to pass.

Adding a new format = one ``register_*`` call. The CLI never has to
know about the new format directly.
"""

from __future__ import annotations

from typing import Callable

from src.parsers.csv_itau_cc import parse_csv_itau_cc
from src.parsers.ofx import parse_ofx, parse_ofx_credit_card
from src.parsers.types import CreditCardStatementData, StatementData


BankParser = Callable[[str], StatementData]
CreditCardParser = Callable[[str], CreditCardStatementData]


_BANK_PARSERS: dict[str, BankParser] = {}
_CREDIT_CARD_PARSERS: dict[str, CreditCardParser] = {}


def register_bank_parser(format: str, parser: BankParser) -> None:
    _BANK_PARSERS[format] = parser


def register_credit_card_parser(
    format: str, parser: CreditCardParser
) -> None:
    _CREDIT_CARD_PARSERS[format] = parser


def list_bank_formats() -> list[str]:
    return sorted(_BANK_PARSERS)


def list_credit_card_formats() -> list[str]:
    return sorted(_CREDIT_CARD_PARSERS)


# --- Auto-detection ------------------------------------------------------


def _looks_like_ofx(content: str) -> bool:
    head = content[:200].upper()
    return "OFXHEADER" in head or head.lstrip().startswith("<OFX")


def _looks_like_csv_itau_cc(content: str) -> bool:
    head = content[:2000].upper()
    return (
        ("MASTERCARD" in head or "VISA" in head)
        and ("VENCIMENTO" in head or "FATURA" in head)
        and ";" in head
    )


def detect_bank_format(content: str) -> str | None:
    if _looks_like_ofx(content):
        return "ofx"
    return None


def detect_credit_card_format(content: str) -> str | None:
    if _looks_like_ofx(content):
        return "ofx-credit-card"
    if _looks_like_csv_itau_cc(content):
        return "csv-itau-cc"
    return None


# --- Entry points --------------------------------------------------------


def parse_bank_statement(
    content: str, *, format: str | None = None
) -> StatementData:
    fmt = format or detect_bank_format(content)
    if fmt is None:
        raise ValueError(
            "could not auto-detect bank statement format; "
            f"pass --format one of: {', '.join(list_bank_formats())}"
        )
    parser = _BANK_PARSERS.get(fmt)
    if parser is None:
        raise ValueError(
            f"unknown bank statement format '{fmt}'; "
            f"registered formats: {', '.join(list_bank_formats())}"
        )
    return parser(content)


def parse_credit_card_statement(
    content: str, *, format: str | None = None
) -> CreditCardStatementData:
    fmt = format or detect_credit_card_format(content)
    if fmt is None:
        raise ValueError(
            "could not auto-detect credit card statement format; "
            f"pass --format one of: {', '.join(list_credit_card_formats())}"
        )
    parser = _CREDIT_CARD_PARSERS.get(fmt)
    if parser is None:
        raise ValueError(
            f"unknown credit card statement format '{fmt}'; "
            f"registered formats: {', '.join(list_credit_card_formats())}"
        )
    return parser(content)


# --- Built-in registrations ---------------------------------------------


register_bank_parser("ofx", parse_ofx)
register_credit_card_parser("ofx-credit-card", parse_ofx_credit_card)
register_credit_card_parser("csv-itau-cc", parse_csv_itau_cc)
