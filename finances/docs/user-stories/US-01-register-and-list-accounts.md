[< User Stories](README.md)

# US-01 — Register and list accounts

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user tracking my personal and business finances,
**I want** to register and list the accounts that hold my money
(checking, credit card, savings, investments),
**so that** every transaction and balance snapshot can be unambiguously
attributed to one account.

An account carries enough metadata to identify it both to a human
(name, bank, agency, masked account number) and to an importer (so OFX
or CSV files can be auto-matched). Each account belongs to an
**entity** (`personal` or `business`) and a **liquidity bucket**
(`liquid`, `semi_liquid`, `illiquid`) that drives runway calculations
later.

### Acceptance value

- `python -m memory ext finances accounts add --name "..." --type checking --entity personal --opening-balance 0 --opening-date 2026-01-01 [--bank ...] [--agency ...] [--account-number ...] [--liquidity liquid]`
- `python -m memory ext finances accounts` lists all accounts, grouped
  by entity, with liquidity bucket and current balance.
- `python -m memory ext finances accounts --entity personal` filters
  by entity.

## Plan

- Pydantic-style model `Account` in `src/models.py`.
- CRUD in `src/store.py` (`create_account`, `get_account`,
  `get_account_by_number`, `list_accounts`, `list_accounts_by_entity`).
- `add_account` registers the account **and** creates an opening
  balance snapshot via the snapshot store (US-02 owns the snapshot
  table; this story just calls into it).
- CLI handler in `src/cli/accounts.py`, wired through
  `extension.register_cli('accounts', ...)`.

## Test Guide

- `add` persists the row and the opening snapshot atomically.
- `list` returns rows ordered by `entity`, `type`, `name`.
- `--entity personal` filters correctly.
- Invalid type / entity / liquidity values rejected with a clear
  message.
- Account number uniqueness is not enforced at the schema level
  (legacy data has duplicates by design when the same bank reuses
  numbers); a warning is emitted but the row is created.
