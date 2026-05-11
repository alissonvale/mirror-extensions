[< User Stories](README.md)

# US-03 — Import bank statement

**Status:** ⚪ Planned

## Story

**As a** user with monthly bank statements,
**I want** to drop a statement file on the CLI and have its
transactions appear in my history,
**so that** I do not have to type each entry by hand.

The first supported format is OFX (Open Financial Exchange), the
de-facto bank export standard in Brazil. The importer is built as a
**parser registry**, so adding new formats later (`csv-<bank>`,
`csv-<bank>-extracts`, etc.) does not change the user-facing command.

### Acceptance value

- `python -m memory ext finances import-statement <file> [--format ofx] [--account <id>]`
- Auto-detects the format from the file header when `--format` is
  omitted.
- Auto-matches the target account by the bank-side account number when
  `--account` is omitted; fails with a clear message if no match is
  found.
- Deduplicates by `fit_id` (the bank-side transaction id) so re-running
  the import is safe.
- After import, records a `source='ofx'` balance snapshot using the
  ledger balance from the file when present.

## Plan

- Parser interface: `parse(content: bytes) -> StatementData` with
  `account_number`, `start_date`, `end_date`, `ledger_balance`,
  `ledger_date`, `transactions: list[RawTransaction]`.
- `src/parsers/ofx.py` ports the legacy `economy/importers/ofx_parser.py`
  with no behavioral change.
- `src/parsers/registry.py` exposes `register_extrato_parser(format,
  fn)` and `parse_extrato(content, format=None)`. Auto-detect via
  signatures (OFX header `OFXHEADER`, magic bytes).
- CLI handler in `src/cli/import_statement.py`.
- Skip lines: the legacy importer filters out `SALDO ANTERIOR`,
  `SALDO TOTAL DISPON` (informational entries from Itaú); this
  behavior is preserved through a `_SKIP_PATTERNS` list defined in
  the parser, not in the CLI.

## Test Guide

- Happy path: small OFX file with three transactions imports three
  rows; `_ext_migrations` not touched; balance snapshot created.
- Re-run is idempotent: same file twice imports zero new rows.
- Auto-match by account number works; mismatch raises a clean error
  pointing at the unmatched account.
- Encoding detection (UTF-8 vs Latin-1) tolerates both.
- Informational entries are skipped.
- Unknown format raises a clear error listing the registered formats.
