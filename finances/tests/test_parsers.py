"""Tests for the parser registry and individual parsers (US-03, US-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.parsers.csv_itau_cc import parse_csv_itau_cc
from src.parsers.ofx import parse_ofx, parse_ofx_credit_card
from src.parsers.registry import (
    detect_bank_format,
    detect_credit_card_format,
    list_bank_formats,
    list_credit_card_formats,
    parse_bank_statement,
    parse_credit_card_statement,
)


FIXTURES = Path(__file__).parent / "fixtures"


# --- OFX parser ----------------------------------------------------------


def test_parse_ofx_extracts_account_period_balance_and_transactions():
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    stmt = parse_ofx(content)
    assert stmt.account_number == "12345-6"
    assert stmt.start_date == "2026-01-01"
    assert stmt.end_date == "2026-01-31"
    assert stmt.ledger_balance == 1500.00
    assert stmt.ledger_date == "2026-01-31"
    # 'SALDO ANTERIOR' is informational and must be skipped.
    assert len(stmt.transactions) == 2
    salary, rent = stmt.transactions
    assert salary.description == "Salary"
    assert salary.amount == 3000.0
    assert salary.type == "credit"
    assert salary.fit_id == "fit-1"
    assert rent.amount == -1500.0
    assert rent.type == "debit"


def test_parse_ofx_rejects_credit_card_file():
    content = """OFXHEADER:100
<OFX>
<CREDITCARDMSGSRSV1>
<CCACCTFROM>
<ACCTID>9999
</CCACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260131
</BANKTRANLIST>
</CREDITCARDMSGSRSV1>
</OFX>
"""
    with pytest.raises(ValueError, match="credit card"):
        parse_ofx(content)


def test_parse_ofx_credit_card_branch():
    content = """OFXHEADER:100
<OFX>
<CREDITCARDMSGSRSV1>
<CCACCTFROM>
<ACCTID>1234567890
</CCACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260131
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260115
<TRNAMT>-99.99
<FITID>cc-1
<MEMO>Online purchase
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>500.00
<DTASOF>20260131
</LEDGERBAL>
</CREDITCARDMSGSRSV1>
</OFX>
"""
    stmt = parse_ofx_credit_card(content)
    assert stmt.card_number == "1234567890"
    assert stmt.total == 500.0
    assert stmt.closing_date == "2026-01-31"
    assert len(stmt.transactions) == 1
    assert stmt.transactions[0].amount == -99.99


# --- CSV Itaú CC parser --------------------------------------------------


def test_parse_csv_itau_cc_extracts_card_total_and_transactions():
    """The legacy parser handled a quirky CSV; build a minimal but
    representative file in memory rather than committing one with real
    bank text."""
    csv_text = """Agência / Conta: 1234/56789-0
MASTERCARD;;;;;;;;;;1234.XXXX.XXXX.5678;;;
vencimento
;;06/03/2026;;;;;;;;;
Total da fatura;;;;;;;;;;RR$1.500,00;
;;Lancamentos nacionais;;;;;;;;;
data;;descricao;;;;;;;;valor;
15/jan.;;Supermercado;;;;;;;;RR$200,00;
20/jan.;;Restaurante;;;;;;;;RR$80,00;
Total de Lancamentos nacionais;;;;;;;;;;RR$280,00;
"""
    stmt = parse_csv_itau_cc(csv_text)
    assert stmt.card_number == "1234.XXXX.XXXX.5678"
    assert stmt.closing_date == "06/03/2026"
    assert stmt.total == 1500.0
    assert len(stmt.transactions) == 2
    sup, rest = stmt.transactions
    assert sup.description == "Supermercado"
    assert sup.amount == -200.0  # credit card line stored as expense
    assert sup.date == "2026-01-15"
    assert sup.type == "debit"
    assert sup.fit_id and len(sup.fit_id) == 16  # generated hash


# --- Registry / auto-detect ----------------------------------------------


def test_registry_lists_registered_formats():
    assert "ofx" in list_bank_formats()
    assert "ofx-credit-card" in list_credit_card_formats()
    assert "csv-itau-cc" in list_credit_card_formats()


def test_detect_bank_format_for_ofx():
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    assert detect_bank_format(content) == "ofx"


def test_detect_credit_card_format_for_csv():
    csv_text = (
        "MASTERCARD;;1234.X.X.5678\n"
        "vencimento\n"
        ";;01/01/2026"
    )
    assert detect_credit_card_format(csv_text) == "csv-itau-cc"


def test_detect_returns_none_for_unknown():
    assert detect_bank_format("hello there\nnot a known format") is None


def test_parse_bank_statement_routes_to_ofx_parser():
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    stmt = parse_bank_statement(content)
    assert stmt.account_number == "12345-6"


def test_parse_bank_statement_unknown_format_raises():
    with pytest.raises(ValueError, match="auto-detect"):
        parse_bank_statement("plain text, not a statement")


def test_parse_bank_statement_explicit_unknown_format_raises():
    content = (FIXTURES / "sample.ofx").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="unknown bank statement format"):
        parse_bank_statement(content, format="nope")


def test_parse_credit_card_statement_routes_to_csv_parser():
    csv_text = """MASTERCARD;;;1234.XXXX.XXXX.0000
vencimento
;;06/03/2026
;;Lancamentos nacionais
data;;descricao;;;;;;;;valor;
15/jan.;;X;;;;;;;;RR$10,00;
"""
    stmt = parse_credit_card_statement(csv_text)
    assert stmt.card_number == "1234.XXXX.XXXX.0000"
    assert len(stmt.transactions) == 1
