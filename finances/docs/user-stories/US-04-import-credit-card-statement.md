[< User Stories](README.md)

# US-04 — Import credit card statement

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user with monthly credit card statements (CSV),
**I want** to drop the file on the CLI and have its purchases appear
in my history,
**so that** credit card spending is part of the consolidated cash flow
without manual transcription.

Credit card statements differ from bank statements in three ways:
they are **closed periods** (no running balance), they are
**debit-only** in normal operation, and they often carry a
**closing date** and a **total** for the period. The importer keeps
the same parser-registry pattern as [US-03](US-03-import-bank-statement.md)
but with a separate command so the difference in semantics is visible.

### Acceptance value

- `python -m memory ext finances import-credit-card-statement <file> [--format csv-itau-cc] [--account <id>]`
- Auto-matches the target account by card-number suffix when
  `--account` is omitted.
- Deduplicates by `fit_id`.
- All imported rows are typed `debit`.

## Plan

- Parser interface mirrors US-03 but returns `CreditCardStatementData`
  with `card_number`, `closing_date`, `total`,
  `transactions: list[RawCreditCardTxn]`.
- `src/parsers/csv_itau_cc.py` ports the legacy
  `economy/importers/itau_csv_parser.py`. The name carries the bank
  only as a format identifier; if other banks ship the same CSV shape
  it can be reused.
- `src/parsers/registry.py` gains `register_fatura_parser` and
  `parse_fatura`.
- CLI handler in `src/cli/import_credit_card.py`.

## Test Guide

- Happy path: small CSV imports rows typed `debit`.
- Re-run is idempotent.
- Auto-match by card suffix; failure raises a clean error.
- Decimal format (Brazilian `1.234,56`) parsed correctly.
- Latin-1 encoding tolerated.
