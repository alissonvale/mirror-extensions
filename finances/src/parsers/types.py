"""Shared shapes for statement parsers.

Two distinct shapes because bank statements and credit card statements
carry meaningfully different metadata: a bank statement reports a
ledger balance on a date; a credit card statement reports a closing
date and a total for the period.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawTransaction:
    """A single transaction extracted from a statement file.

    Mirrors the ext_finances_transactions column set verbatim so the
    importer can map row by row without any per-format adapter logic.
    """

    date: str             # ISO date
    description: str
    amount: float         # positive = credit, negative = debit
    type: str             # 'credit' | 'debit'
    fit_id: str | None = None


@dataclass
class StatementData:
    """Parsed bank statement (any format)."""

    account_number: str | None
    start_date: str | None
    end_date: str | None
    ledger_balance: float | None
    ledger_date: str | None
    transactions: list[RawTransaction] = field(default_factory=list)


@dataclass
class CreditCardStatementData:
    """Parsed credit card statement (any format)."""

    card_number: str | None
    closing_date: str | None
    total: float | None
    transactions: list[RawTransaction] = field(default_factory=list)
