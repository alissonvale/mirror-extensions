"""Tests for the categorization path (US-09)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.cli.categories import cmd_categories, cmd_categorize
from src.store import get_category, list_categories
from src.store_writes import (
    assign_category_to_transaction,
    create_account,
    create_category,
    delete_category,
    get_or_create_category,
)


def _seed_transaction(api, account_id: str, txn_id: str = "txn1") -> str:
    api.execute(
        "INSERT INTO ext_finances_transactions "
        "(id, account_id, date, description, amount, type, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            txn_id,
            account_id,
            "2026-02-15",
            "supermarket",
            -123.45,
            "debit",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    api.commit()
    return txn_id


# --- store_writes -------------------------------------------------------


def test_create_category_persists(finances_api):
    cat_id = create_category(finances_api, name="Groceries", type="expense")
    cats = list_categories(finances_api)
    assert len(cats) == 1
    assert cats[0].id == cat_id
    assert cats[0].name == "Groceries"
    assert cats[0].type == "expense"


def test_create_category_rejects_duplicate_name(finances_api):
    create_category(finances_api, name="Rent", type="expense")
    with pytest.raises(ValueError, match="already exists"):
        create_category(finances_api, name="Rent", type="expense")


def test_create_category_rejects_invalid_type(finances_api):
    with pytest.raises(ValueError, match="invalid type"):
        create_category(finances_api, name="Mystery", type="unknown")


def test_get_or_create_category_returns_existing_id(finances_api):
    first = create_category(finances_api, name="Coffee", type="expense")
    second = get_or_create_category(finances_api, name="coffee", type="expense")
    assert first == second  # case-insensitive lookup


def test_get_or_create_category_creates_when_missing(finances_api):
    cat_id = get_or_create_category(finances_api, name="NewCat", type="income")
    assert get_category(finances_api, cat_id) is not None


def test_delete_category_works_when_unreferenced(finances_api):
    cat_id = create_category(finances_api, name="Tmp", type="expense")
    assert delete_category(finances_api, cat_id) is True
    assert list_categories(finances_api) == []


def test_delete_category_blocked_when_referenced(finances_api):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    cat_id = create_category(finances_api, name="Used", type="expense")
    txn_id = _seed_transaction(finances_api, account_id)
    assign_category_to_transaction(
        finances_api, transaction_id=txn_id, category_id=cat_id
    )
    with pytest.raises(ValueError, match="referenced by 1"):
        delete_category(finances_api, cat_id)


def test_assign_and_clear_category_on_transaction(finances_api):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    cat_id = create_category(finances_api, name="Food", type="expense")
    txn_id = _seed_transaction(finances_api, account_id)

    assert assign_category_to_transaction(
        finances_api, transaction_id=txn_id, category_id=cat_id
    )
    row = finances_api.read(
        "SELECT category_id FROM ext_finances_transactions WHERE id = ?",
        (txn_id,),
    ).fetchone()
    assert row["category_id"] == cat_id

    assert assign_category_to_transaction(
        finances_api, transaction_id=txn_id, category_id=None
    )
    row = finances_api.read(
        "SELECT category_id FROM ext_finances_transactions WHERE id = ?",
        (txn_id,),
    ).fetchone()
    assert row["category_id"] is None


# --- CLI: categories ----------------------------------------------------


def test_cli_categories_list_empty(finances_api, capsys):
    rc = cmd_categories(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(no categories)" in out


def test_cli_categories_add_and_list(finances_api, capsys):
    rc = cmd_categories(finances_api, ["add", "Travel", "expense"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "added category" in out
    rc = cmd_categories(finances_api, ["list"])
    out = capsys.readouterr().out
    assert "Travel" in out
    assert "expense" in out


def test_cli_categories_add_invalid_type(finances_api, capsys):
    rc = cmd_categories(finances_api, ["add", "X", "wat"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid type" in out


def test_cli_categories_remove(finances_api, capsys):
    create_category(finances_api, name="Tmp", type="expense")
    cat_id = list_categories(finances_api)[0].id
    rc = cmd_categories(finances_api, ["remove", cat_id])
    out = capsys.readouterr().out
    assert rc == 0
    assert "removed category" in out


def test_cli_categories_remove_unknown(finances_api, capsys):
    rc = cmd_categories(finances_api, ["remove", "ghost"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no category" in out


def test_cli_categories_help(finances_api, capsys):
    rc = cmd_categories(finances_api, ["--help"])
    assert rc == 0
    assert "usage:" in capsys.readouterr().out


# --- CLI: categorize ----------------------------------------------------


def test_cli_categorize_by_id(finances_api, capsys):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    cat_id = create_category(finances_api, name="Food", type="expense")
    txn_id = _seed_transaction(finances_api, account_id)

    rc = cmd_categorize(finances_api, [txn_id, cat_id])
    out = capsys.readouterr().out
    assert rc == 0
    assert "categorized" in out


def test_cli_categorize_by_name(finances_api, capsys):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    create_category(finances_api, name="Coffee", type="expense")
    txn_id = _seed_transaction(finances_api, account_id)

    rc = cmd_categorize(finances_api, [txn_id, "COFFEE"])  # case-insensitive
    out = capsys.readouterr().out
    assert rc == 0
    assert "categorized" in out


def test_cli_categorize_auto_create_with_type(finances_api, capsys):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    txn_id = _seed_transaction(finances_api, account_id)
    rc = cmd_categorize(
        finances_api, [txn_id, "NewBucket", "--type", "expense"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    cats = list_categories(finances_api)
    assert any(c.name == "NewBucket" for c in cats)


def test_cli_categorize_missing_category_without_type(finances_api, capsys):
    account_id = create_account(
        finances_api, name="A", type="checking", entity="personal"
    )
    txn_id = _seed_transaction(finances_api, account_id)
    rc = cmd_categorize(finances_api, [txn_id, "Unknown"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no category matches" in out


def test_cli_categorize_unknown_transaction(finances_api, capsys):
    create_category(finances_api, name="Food", type="expense")
    rc = cmd_categorize(finances_api, ["ghost", "Food"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no transaction with id" in out


def test_cli_categorize_too_few_args(finances_api, capsys):
    rc = cmd_categorize(finances_api, ["only-one-arg"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "requires" in out
