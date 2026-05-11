"""Tests for statement import orchestration and CLI (US-03 / US-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cli.import_statement import (
    cmd_import_credit_card_statement,
    cmd_import_statement,
)
from src.import_statement import (
    import_bank_statement,
    import_credit_card_statement,
    read_statement_file,
)
from src.store import get_latest_snapshot, list_transactions
from src.store_writes import create_account


FIXTURES = Path(__file__).parent / "fixtures"


# --- read_statement_file -------------------------------------------------


def test_read_statement_file_detects_utf8(tmp_path):
    p = tmp_path / "utf8.txt"
    p.write_bytes("ENCODING:UTF-8\nolá\n".encode("utf-8"))
    content = read_statement_file(p)
    assert "olá" in content


def test_read_statement_file_falls_back_to_latin1(tmp_path):
    p = tmp_path / "latin.txt"
    # 'Ação' encoded as Latin-1 is invalid as UTF-8: the decoder
    # would either raise or replace bytes with U+FFFD. Confirm the
    # reader detects this and returns proper text.
    p.write_bytes("Ação".encode("latin-1"))
    content = read_statement_file(p)
    assert content == "Ação"


# --- import_bank_statement ----------------------------------------------


def test_import_bank_statement_inserts_transactions_and_snapshot(finances_api):
    create_account(
        finances_api,
        name="Personal Checking",
        type="checking",
        entity="personal",
        opening_balance=0,
        opening_date="2026-01-01",
        account_number="12345-6",
    )

    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    result = import_bank_statement(finances_api, content=content)

    # Two real txns from the fixture; SALDO ANTERIOR was skipped.
    assert result.imported == 2
    assert result.skipped == 0
    assert result.period == "2026-01-01 to 2026-01-31"
    assert result.ledger_balance == 1500.00

    txns = list_transactions(finances_api)
    assert len(txns) == 2
    assert {t.fit_id for t in txns} == {"fit-1", "fit-2"}

    # Ledger snapshot recorded.
    snap = get_latest_snapshot(finances_api, result.account_id)
    assert snap is not None
    assert snap.balance == 1500.00
    assert snap.source == "ofx"


def test_import_bank_statement_is_idempotent(finances_api):
    create_account(
        finances_api,
        name="A",
        type="checking",
        entity="personal",
        account_number="12345-6",
        opening_date="2026-01-01",
    )
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    first = import_bank_statement(finances_api, content=content)
    second = import_bank_statement(finances_api, content=content)
    assert first.imported == 2
    assert second.imported == 0
    assert second.skipped == 2


def test_import_bank_statement_no_account_match_raises(finances_api):
    create_account(
        finances_api,
        name="A",
        type="checking",
        entity="personal",
        account_number="other",
        opening_date="2026-01-01",
    )
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="could not match"):
        import_bank_statement(finances_api, content=content)


def test_import_bank_statement_with_explicit_account(finances_api):
    account_id = create_account(
        finances_api,
        name="Generic",
        type="checking",
        entity="personal",
        opening_date="2026-01-01",
    )
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    result = import_bank_statement(
        finances_api, content=content, account_id=account_id
    )
    assert result.account_id == account_id
    assert result.imported == 2


# --- import_credit_card_statement --------------------------------------


def test_import_credit_card_statement_inserts_no_snapshot(finances_api):
    """Credit card imports do NOT record a snapshot (credit cards do
    not have a running balance)."""
    csv_text = """MASTERCARD;;;1234.XXXX.XXXX.0000
vencimento
;;06/03/2026
;;Lancamentos nacionais
data;;descricao;;;;;;;;valor;
15/jan.;;Restaurant;;;;;;;;RR$50,00;
"""
    account_id = create_account(
        finances_api,
        name="Card",
        type="credit_card",
        entity="personal",
        account_number="0000",
        opening_date="2026-01-01",
    )
    result = import_credit_card_statement(
        finances_api, content=csv_text, account_id=account_id
    )
    assert result.imported == 1
    # The only snapshot is the opening one (no 'ofx' source).
    snap = get_latest_snapshot(finances_api, account_id)
    assert snap.source == "opening"


# --- CLI: import-statement ----------------------------------------------


def test_cli_import_statement_happy_path(finances_api, capsys):
    create_account(
        finances_api,
        name="Personal Checking",
        type="checking",
        entity="personal",
        account_number="12345-6",
        opening_date="2026-01-01",
    )
    path = FIXTURES / "sample.ofx"
    rc = cmd_import_statement(finances_api, [str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "rows: 2 new, 0 skipped" in out
    assert "ledger balance: R$ 1.500,00" in out
    assert "period: 2026-01-01 to 2026-01-31" in out


def test_cli_import_statement_missing_file(finances_api, capsys, tmp_path):
    rc = cmd_import_statement(finances_api, [str(tmp_path / "nope.ofx")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "file not found" in out


def test_cli_import_statement_explicit_account(finances_api, capsys):
    account_id = create_account(
        finances_api,
        name="Generic",
        type="checking",
        entity="personal",
        opening_date="2026-01-01",
    )
    path = FIXTURES / "sample.ofx"
    rc = cmd_import_statement(
        finances_api, [str(path), "--account", account_id]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert account_id in out


def test_cli_import_statement_no_args(finances_api, capsys):
    rc = cmd_import_statement(finances_api, [])
    out = capsys.readouterr().out
    assert rc == 1
    assert "<file> is required" in out


def test_cli_import_statement_unrecognised_flag(finances_api, capsys):
    path = FIXTURES / "sample.ofx"
    rc = cmd_import_statement(finances_api, [str(path), "--rocket", "fuel"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unrecognised argument" in out


# --- CLI: import-credit-card-statement ---------------------------------


def test_cli_import_credit_card_happy_path(finances_api, tmp_path, capsys):
    csv_path = tmp_path / "card.csv"
    csv_path.write_text(
        "MASTERCARD;;;1234.XXXX.XXXX.0000\n"
        "vencimento\n"
        ";;06/03/2026\n"
        "Total da fatura;;;;;;;;;;RR$50,00;\n"
        ";;Lancamentos nacionais\n"
        "data;;descricao;;;;;;;;valor;\n"
        "15/jan.;;Restaurant;;;;;;;;RR$50,00;\n",
        encoding="utf-8",
    )
    account_id = create_account(
        finances_api,
        name="Card",
        type="credit_card",
        entity="personal",
        account_number="0000",
        opening_date="2026-01-01",
    )
    rc = cmd_import_credit_card_statement(finances_api, [str(csv_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "rows: 1 new" in out
    assert "statement total: R$ 50,00" in out
    # Account auto-matched by card-suffix '0000'.
    assert account_id in out
