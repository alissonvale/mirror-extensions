"""Read helpers over the ext_finances_* tables.

Stateless module-level functions that take the ExtensionAPI and return
typed models. Writes live elsewhere (each user story owns its own
write path); this module is only the read surface that the reports
and the Mirror Mode provider need.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.models import (
    Account,
    BalanceSnapshot,
    Category,
    RecurringBill,
    Transaction,
)

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


def _row_to_account(row) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        entity=row["entity"],
        liquidity=row["liquidity"],
        opening_balance=row["opening_balance"],
        opening_date=row["opening_date"],
        bank=row["bank"],
        agency=row["agency"],
        account_number=row["account_number"],
        metadata=row["metadata"],
        created_at=row["created_at"],
    )


def _row_to_transaction(row) -> Transaction:
    return Transaction(
        id=row["id"],
        account_id=row["account_id"],
        date=row["date"],
        description=row["description"],
        amount=row["amount"],
        type=row["type"],
        memo=row["memo"],
        category_id=row["category_id"],
        fit_id=row["fit_id"],
        balance_after=row["balance_after"],
        metadata=row["metadata"],
        created_at=row["created_at"],
    )


def _row_to_snapshot(row) -> BalanceSnapshot:
    return BalanceSnapshot(
        id=row["id"],
        account_id=row["account_id"],
        date=row["date"],
        balance=row["balance"],
        source=row["source"],
        created_at=row["created_at"],
    )


def _row_to_bill(row) -> RecurringBill:
    return RecurringBill(
        id=row["id"],
        name=row["name"],
        entity=row["entity"],
        category=row["category"],
        amount=row["amount"],
        active=bool(row["active"]),
        day_of_month=row["day_of_month"],
        notes=row["notes"],
        created_at=row["created_at"],
    )


def list_accounts(api: "ExtensionAPI") -> list[Account]:
    rows = api.read(
        "SELECT * FROM ext_finances_accounts ORDER BY entity, type, name"
    ).fetchall()
    return [_row_to_account(r) for r in rows]


def get_latest_snapshot(
    api: "ExtensionAPI", account_id: str
) -> BalanceSnapshot | None:
    row = api.read(
        "SELECT * FROM ext_finances_balance_snapshots "
        "WHERE account_id = ? "
        "ORDER BY date DESC, created_at DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    return _row_to_snapshot(row) if row else None


def list_transactions(
    api: "ExtensionAPI",
    *,
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    category_id: str | None = None,
    type: str | None = None,
    description_like: str | None = None,
) -> list[Transaction]:
    """List transactions with optional filters.

    Every filter is AND-composed. ``description_like`` does a
    case-insensitive substring match. Without filters, returns every
    row ordered by date ascending.
    """
    clauses: list[str] = []
    params: list[object] = []
    if account_id:
        clauses.append("account_id = ?")
        params.append(account_id)
    if start_date:
        clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("date <= ?")
        params.append(end_date)
    if category_id:
        clauses.append("category_id = ?")
        params.append(category_id)
    if type:
        clauses.append("type = ?")
        params.append(type)
    if description_like:
        clauses.append("LOWER(description) LIKE ?")
        params.append(f"%{description_like.lower()}%")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = api.read(
        f"SELECT * FROM ext_finances_transactions{where} "
        f"ORDER BY date, created_at",
        params,
    ).fetchall()
    return [_row_to_transaction(r) for r in rows]


def list_active_bills(api: "ExtensionAPI") -> list[RecurringBill]:
    rows = api.read(
        "SELECT * FROM ext_finances_recurring_bills "
        "WHERE active = 1 ORDER BY entity, name"
    ).fetchall()
    return [_row_to_bill(r) for r in rows]


def _row_to_category(row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        created_at=row["created_at"],
    )


def list_categories(api: "ExtensionAPI") -> list[Category]:
    rows = api.read(
        "SELECT * FROM ext_finances_categories ORDER BY type, name"
    ).fetchall()
    return [_row_to_category(r) for r in rows]


def get_category_by_name(
    api: "ExtensionAPI", name: str
) -> Category | None:
    row = api.read(
        "SELECT * FROM ext_finances_categories WHERE LOWER(name) = LOWER(?)",
        (name,),
    ).fetchone()
    return _row_to_category(row) if row else None


def get_category(api: "ExtensionAPI", category_id: str) -> Category | None:
    row = api.read(
        "SELECT * FROM ext_finances_categories WHERE id = ?",
        (category_id,),
    ).fetchone()
    return _row_to_category(row) if row else None
