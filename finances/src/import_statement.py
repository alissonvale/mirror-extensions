"""Bank-statement and credit-card-statement import orchestration.

Given a parsed statement and (optionally) a target account, this
module turns its transactions into rows in ``ext_finances_transactions``
and, for bank statements, appends a balance snapshot.

Dedup is by ``fit_id`` (the bank-side transaction id, or a stable hash
when the source ships none). Re-running an import is a no-op.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src.parsers.registry import (
    parse_bank_statement,
    parse_credit_card_statement,
)
from src.parsers.types import (
    CreditCardStatementData,
    RawTransaction,
    StatementData,
)
from src.store import list_accounts
from src.store_writes import new_id, now_utc_iso, record_snapshot

if TYPE_CHECKING:
    from memory.extensions.api import ExtensionAPI


@dataclass
class ImportResult:
    account_id: str
    imported: int = 0
    skipped: int = 0
    period: str | None = None
    ledger_balance: float | None = None
    closing_date: str | None = None
    total: float | None = None
    warnings: list[str] = field(default_factory=list)


# --- File loading --------------------------------------------------------


def read_statement_file(path: Path) -> str:
    """Read a statement file, picking the right encoding.

    OFX exports declare encoding in the header line; everything else
    is Latin-1 in practice (Brazilian bank exports). UTF-8 wins when
    declared; Latin-1 is the safe fallback for anything that is not
    obviously UTF-8.
    """
    raw = path.read_bytes()
    head = raw[:500].decode("ascii", errors="ignore").upper()
    if "UTF-8" in head or "UTF8" in head:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    try:
        return raw.decode("latin-1")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


# --- Account matching ----------------------------------------------------


def _match_account_by_number(
    api: "ExtensionAPI", number_or_suffix: str | None
) -> str | None:
    if not number_or_suffix:
        return None
    # Try exact, then suffix-of-suffix (last 4 digits of legacy card numbers).
    accounts = list_accounts(api)
    for acc in accounts:
        if acc.account_number and acc.account_number == number_or_suffix:
            return acc.id
    suffix = number_or_suffix.split(".")[-1]
    for acc in accounts:
        if acc.account_number and suffix and suffix in acc.account_number:
            return acc.id
    return None


# --- Importers -----------------------------------------------------------


def _existing_fit_ids(api: "ExtensionAPI", account_id: str) -> set[str]:
    rows = api.read(
        "SELECT fit_id FROM ext_finances_transactions "
        "WHERE account_id = ? AND fit_id IS NOT NULL",
        (account_id,),
    ).fetchall()
    return {row[0] for row in rows}


def _insert_transactions(
    api: "ExtensionAPI",
    *,
    account_id: str,
    transactions: list[RawTransaction],
) -> tuple[int, int]:
    existing = _existing_fit_ids(api, account_id)
    imported = 0
    skipped = 0
    created_at = now_utc_iso()
    with api.transaction():
        for txn in transactions:
            if txn.fit_id and txn.fit_id in existing:
                skipped += 1
                continue
            api.execute(
                "INSERT INTO ext_finances_transactions "
                "(id, account_id, date, description, memo, amount, type, "
                " fit_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id(),
                    account_id,
                    txn.date,
                    txn.description,
                    txn.description,
                    txn.amount,
                    txn.type,
                    txn.fit_id,
                    created_at,
                ),
            )
            if txn.fit_id:
                existing.add(txn.fit_id)
            imported += 1
    return imported, skipped


def import_bank_statement(
    api: "ExtensionAPI",
    *,
    content: str,
    format: str | None = None,
    account_id: str | None = None,
) -> ImportResult:
    """Parse + import a bank statement.

    Auto-matches the account by ``account_number`` when ``account_id``
    is omitted. After importing transactions, records a
    ``source='ofx'`` snapshot with the ledger balance from the file if
    one is available.
    """
    statement: StatementData = parse_bank_statement(content, format=format)

    target_account_id = account_id or _match_account_by_number(
        api, statement.account_number
    )
    if target_account_id is None:
        raise ValueError(
            "could not match a registered account from the statement "
            f"(file account_number={statement.account_number!r}); "
            "pass --account <id> explicitly"
        )

    imported, skipped = _insert_transactions(
        api,
        account_id=target_account_id,
        transactions=statement.transactions,
    )

    result = ImportResult(
        account_id=target_account_id,
        imported=imported,
        skipped=skipped,
        ledger_balance=statement.ledger_balance,
    )
    if statement.start_date and statement.end_date:
        result.period = f"{statement.start_date} to {statement.end_date}"

    if (
        statement.ledger_balance is not None
        and statement.ledger_date
    ):
        record_snapshot(
            api,
            account_id=target_account_id,
            date=statement.ledger_date,
            balance=statement.ledger_balance,
            source="ofx",
        )

    return result


def import_credit_card_statement(
    api: "ExtensionAPI",
    *,
    content: str,
    format: str | None = None,
    account_id: str | None = None,
) -> ImportResult:
    """Parse + import a credit card statement.

    No balance snapshot is recorded: credit card statements report
    closing totals, not running balances.
    """
    statement: CreditCardStatementData = parse_credit_card_statement(
        content, format=format
    )

    target_account_id = account_id or _match_account_by_number(
        api, statement.card_number
    )
    if target_account_id is None:
        raise ValueError(
            "could not match a registered account from the statement "
            f"(card_number={statement.card_number!r}); "
            "pass --account <id> explicitly"
        )

    imported, skipped = _insert_transactions(
        api,
        account_id=target_account_id,
        transactions=statement.transactions,
    )

    return ImportResult(
        account_id=target_account_id,
        imported=imported,
        skipped=skipped,
        closing_date=statement.closing_date,
        total=statement.total,
    )
