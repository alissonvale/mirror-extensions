"""OFX (Open Financial Exchange) parser for bank statements.

Ported from the legacy ``economy/importers/ofx_parser.py`` with a
single semantic change: it returns the
:class:`StatementData` shape from ``parsers.types``, not an
OFX-specific dataclass, so the importer is format-agnostic.

Supports both bank statements (``BANKMSGSRSV1``) and credit card
statements (``CREDITCARDMSGSRSV1``); the credit-card branch is exposed
through ``parse_ofx_credit_card`` so the bank importer never sees
credit-card data and vice versa.
"""

from __future__ import annotations

import re

from src.parsers.types import (
    CreditCardStatementData,
    RawTransaction,
    StatementData,
)


def _parse_date(raw: str) -> str:
    """Convert OFX date (YYYYMMDD...) to ISO YYYY-MM-DD."""
    clean = raw.strip()[:8]
    return f"{clean[:4]}-{clean[4:6]}-{clean[6:8]}"


def _extract_tag(content: str, tag: str) -> str | None:
    """Extract value of a self-closing SGML tag."""
    pattern = rf"<{tag}>([^<\n]+)"
    match = re.search(pattern, content, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_block(content: str, tag: str) -> str | None:
    """Extract content between <TAG> and </TAG>."""
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else None


# Itaú-flavoured OFX exports include informational entries that are not
# real transactions — they represent the running balance line and a
# 'total available' line. Skip them; otherwise they would inflate the
# transaction history with phantom 'rows'.
_SKIP_DESCRIPTION_PATTERNS = ("SALDO ANTERIOR", "SALDO TOTAL DISPON")


def _looks_like_credit_card(content: str) -> bool:
    return "CREDITCARDMSGSRSV1" in content.upper()


def _extract_transactions(trans_list: str) -> list[RawTransaction]:
    blocks = re.findall(
        r"<STMTTRN>(.*?)</STMTTRN>", trans_list, re.DOTALL | re.IGNORECASE
    )
    out: list[RawTransaction] = []
    for block in blocks:
        memo = _extract_tag(block, "MEMO") or ""
        memo_upper = memo.upper()
        if any(pat in memo_upper for pat in _SKIP_DESCRIPTION_PATTERNS):
            continue
        amount = float(_extract_tag(block, "TRNAMT") or "0")
        out.append(
            RawTransaction(
                date=_parse_date(_extract_tag(block, "DTPOSTED") or ""),
                description=memo,
                amount=amount,
                type="credit" if amount >= 0 else "debit",
                fit_id=_extract_tag(block, "FITID"),
            )
        )
    return out


def parse_ofx(content: str) -> StatementData:
    """Parse a bank-statement OFX file.

    Raises ``ValueError`` if the file looks like a credit card
    statement (the caller should use the credit-card importer
    instead).
    """
    if _looks_like_credit_card(content):
        raise ValueError(
            "this OFX file looks like a credit card statement; "
            "use the credit-card importer instead"
        )

    acct_block = _extract_block(content, "BANKACCTFROM")
    account_number = _extract_tag(acct_block, "ACCTID") if acct_block else None

    trans_list = _extract_block(content, "BANKTRANLIST")
    start_date = _parse_date(_extract_tag(trans_list, "DTSTART") or "") if trans_list else None
    end_date = _parse_date(_extract_tag(trans_list, "DTEND") or "") if trans_list else None

    ledger_block = _extract_block(content, "LEDGERBAL")
    ledger_balance = (
        float(_extract_tag(ledger_block, "BALAMT") or "0") if ledger_block else None
    )
    ledger_date = (
        _parse_date(_extract_tag(ledger_block, "DTASOF") or "")
        if ledger_block
        else None
    )

    transactions = _extract_transactions(trans_list) if trans_list else []

    return StatementData(
        account_number=account_number,
        start_date=start_date,
        end_date=end_date,
        ledger_balance=ledger_balance,
        ledger_date=ledger_date,
        transactions=transactions,
    )


def parse_ofx_credit_card(content: str) -> CreditCardStatementData:
    """Parse a credit-card OFX file (CREDITCARDMSGSRSV1)."""
    if not _looks_like_credit_card(content):
        raise ValueError(
            "this OFX file does not look like a credit card statement"
        )

    acct_block = _extract_block(content, "CCACCTFROM")
    card_number = _extract_tag(acct_block, "ACCTID") if acct_block else None

    trans_list = _extract_block(content, "BANKTRANLIST")
    end_date = (
        _parse_date(_extract_tag(trans_list, "DTEND") or "") if trans_list else None
    )

    ledger_block = _extract_block(content, "LEDGERBAL")
    total = (
        float(_extract_tag(ledger_block, "BALAMT") or "0") if ledger_block else None
    )

    transactions = _extract_transactions(trans_list) if trans_list else []

    return CreditCardStatementData(
        card_number=card_number,
        closing_date=end_date,
        total=total,
        transactions=transactions,
    )
