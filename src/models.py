"""Lightweight typed views over the ext_finances_* rows.

These models are read-only by design: they describe a row, not an
identity. CRUD happens through ``store.py`` functions that map back
and forth from SQLite rows. Pure dataclasses, no validation library
dependency — the schema constraints already cover validation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    type: str                 # 'checking' | 'credit_card' | 'savings'
    entity: str               # 'personal' | 'business'
    liquidity: str            # 'liquid' | 'semi_liquid' | 'illiquid'
    opening_balance: float
    opening_date: str
    bank: str | None = None
    agency: str | None = None
    account_number: str | None = None
    metadata: str | None = None
    created_at: str = ""


@dataclass(frozen=True)
class Transaction:
    id: str
    account_id: str
    date: str
    description: str
    amount: float             # positive = credit, negative = debit
    type: str                 # 'credit' | 'debit'
    memo: str | None = None
    category_id: str | None = None
    fit_id: str | None = None
    balance_after: float | None = None
    metadata: str | None = None
    created_at: str = ""


@dataclass(frozen=True)
class BalanceSnapshot:
    id: str
    account_id: str
    date: str
    balance: float
    source: str = "manual"
    created_at: str = ""


@dataclass(frozen=True)
class RecurringBill:
    id: str
    name: str
    entity: str               # 'personal' | 'business'
    category: str             # 'fixed' | 'variable' (volatility, not topic)
    amount: float             # negative for expenses by convention
    active: bool = True
    day_of_month: int | None = None
    notes: str | None = None
    created_at: str = ""
