"""Write helpers over the ext_finances_* tables.

Companion to ``store.py`` (read helpers). Split keeps the read path
free of any mutation logic; this module owns every INSERT and UPDATE
the extension's CLI subcommands fire.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


# --- ID and timestamp helpers --------------------------------------------


def new_id() -> str:
    """Generate the same 8-char hex shape the legacy schema used.

    Keeping the same shape across legacy and new rows means a foreign
    reference (e.g. a memory mentioning 'acc00001') stays valid no
    matter when the row was created.
    """
    return uuid.uuid4().hex[:8]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_iso() -> str:
    """ISO date for 'today'. Used as a default for opening_date when omitted."""
    return datetime.now(timezone.utc).date().isoformat()


# --- Validation helpers --------------------------------------------------


VALID_ACCOUNT_TYPES = {"checking", "credit_card", "savings"}
VALID_ENTITIES = {"personal", "business"}
VALID_LIQUIDITIES = {"liquid", "semi_liquid", "illiquid"}
VALID_SNAPSHOT_SOURCES = {"manual", "ofx", "opening", "reconciliation"}
VALID_BILL_CATEGORIES = {"fixed", "variable"}
VALID_CATEGORY_TYPES = {"income", "expense", "transfer"}


def _require(value, valid: set[str], field: str) -> str:
    if value not in valid:
        raise ValueError(
            f"invalid {field}: {value!r} (expected one of {sorted(valid)})"
        )
    return value


# --- Accounts (US-01) ----------------------------------------------------


def create_account(
    api: "ExtensionAPI",
    *,
    name: str,
    type: str,
    entity: str,
    opening_balance: float = 0.0,
    opening_date: str | None = None,
    bank: str | None = None,
    agency: str | None = None,
    account_number: str | None = None,
    liquidity: str = "liquid",
    metadata: str | None = None,
) -> str:
    """Create an account row + its opening balance snapshot atomically.

    Returns the new account id. Validates enum-shaped fields locally so
    the user gets a clear error before the SQL runs.
    """
    _require(type, VALID_ACCOUNT_TYPES, "type")
    _require(entity, VALID_ENTITIES, "entity")
    _require(liquidity, VALID_LIQUIDITIES, "liquidity")

    account_id = new_id()
    opening = opening_date or today_iso()
    created = now_utc_iso()

    with api.transaction():
        api.execute(
            "INSERT INTO ext_finances_accounts "
            "(id, name, bank, agency, account_number, type, entity, liquidity, "
            " opening_balance, opening_date, created_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                account_id,
                name,
                bank,
                agency,
                account_number,
                type,
                entity,
                liquidity,
                opening_balance,
                opening,
                created,
                metadata,
            ),
        )
        api.execute(
            "INSERT INTO ext_finances_balance_snapshots "
            "(id, account_id, date, balance, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_id(),
                account_id,
                opening,
                opening_balance,
                "opening",
                created,
            ),
        )
    return account_id


# --- Balance snapshots (US-02) -------------------------------------------


def record_snapshot(
    api: "ExtensionAPI",
    *,
    account_id: str,
    date: str,
    balance: float,
    source: str = "manual",
) -> str:
    """Append a snapshot. Returns the new snapshot id."""
    _require(source, VALID_SNAPSHOT_SOURCES, "source")
    snap_id = new_id()
    api.execute(
        "INSERT INTO ext_finances_balance_snapshots "
        "(id, account_id, date, balance, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (snap_id, account_id, date, balance, source, now_utc_iso()),
    )
    api.commit()
    return snap_id


# --- Recurring bills (US-06) ---------------------------------------------


def create_bill(
    api: "ExtensionAPI",
    *,
    name: str,
    entity: str,
    category: str,
    amount: float,
    day_of_month: int | None = None,
    notes: str | None = None,
) -> str:
    """Create a recurring bill. Amount is stored as-is.

    The reports layer expects expenses as negative numbers (the runway
    helper sums without sign-flipping). Callers that pass positive
    expense amounts are silently sign-flipped to match the convention.
    """
    _require(entity, VALID_ENTITIES, "entity")
    _require(category, VALID_BILL_CATEGORIES, "category")

    # Expenses are negative by convention; auto-flip positive inputs.
    stored_amount = -abs(amount) if amount > 0 else amount

    bill_id = new_id()
    api.execute(
        "INSERT INTO ext_finances_recurring_bills "
        "(id, name, entity, category, amount, day_of_month, notes, "
        " active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
        (
            bill_id,
            name,
            entity,
            category,
            stored_amount,
            day_of_month,
            notes,
            now_utc_iso(),
        ),
    )
    api.commit()
    return bill_id


def deactivate_bill(api: "ExtensionAPI", bill_id: str) -> bool:
    """Toggle a bill's active flag to 0. Returns True when a row was changed."""
    cursor = api.execute(
        "UPDATE ext_finances_recurring_bills SET active = 0 WHERE id = ?",
        (bill_id,),
    )
    api.commit()
    return (cursor.rowcount or 0) > 0


# --- Categories (US-09) --------------------------------------------------


def create_category(api: "ExtensionAPI", *, name: str, type: str) -> str:
    """Create a transaction category. Returns the new id.

    Names are unique at the schema level. Duplicate names raise
    ``ValueError`` instead of leaking ``sqlite3.IntegrityError``.
    """
    _require(type, VALID_CATEGORY_TYPES, "type")
    cat_id = new_id()
    try:
        api.execute(
            "INSERT INTO ext_finances_categories "
            "(id, name, type, created_at) VALUES (?, ?, ?, ?)",
            (cat_id, name, type, now_utc_iso()),
        )
        api.commit()
    except Exception as exc:
        # The schema enforces UNIQUE(name); surface a friendly error.
        message = str(exc).lower()
        if "unique" in message:
            raise ValueError(f"category '{name}' already exists") from exc
        raise
    return cat_id


def get_or_create_category(
    api: "ExtensionAPI", *, name: str, type: str
) -> str:
    """Return an existing category's id (by name) or create a new one."""
    from src.store import get_category_by_name

    existing = get_category_by_name(api, name)
    if existing:
        return existing.id
    return create_category(api, name=name, type=type)


def delete_category(api: "ExtensionAPI", category_id: str) -> bool:
    """Delete a category if no transaction references it.

    Returns True on deletion, False when the id is unknown. Raises
    ``ValueError`` if at least one transaction still points at this
    category, naming the count.
    """
    count = api.read(
        "SELECT COUNT(*) AS c FROM ext_finances_transactions "
        "WHERE category_id = ?",
        (category_id,),
    ).fetchone()["c"]
    if count:
        raise ValueError(
            f"category {category_id} is referenced by {count} "
            f"transaction(s); reassign them first"
        )
    cursor = api.execute(
        "DELETE FROM ext_finances_categories WHERE id = ?", (category_id,)
    )
    api.commit()
    return (cursor.rowcount or 0) > 0


def assign_category_to_transaction(
    api: "ExtensionAPI", *, transaction_id: str, category_id: str | None
) -> bool:
    """Set or clear a transaction's category. Returns True when changed."""
    cursor = api.execute(
        "UPDATE ext_finances_transactions SET category_id = ? WHERE id = ?",
        (category_id, transaction_id),
    )
    api.commit()
    return (cursor.rowcount or 0) > 0
