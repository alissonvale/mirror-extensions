[< User Stories](README.md)

# US-05 — List and filter transactions

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user investigating my spending,
**I want** to list transactions with simple filters (account, date
range, category),
**so that** I can answer questions like "how much did I spend on
groceries in May?" or "show me every transfer from the business
account in Q1".

### Acceptance value

- `python -m memory ext finances transactions [--account <id>] [--from <date>] [--to <date>] [--category <id>] [--type credit|debit] [--description <substring>]`
- Output is a table (or JSON with `--json`) sorted by date ascending.

## Plan

- Store: `list_transactions(account_id, start_date, end_date,
  category_id, type, description_like)`.
- CLI handler in `src/cli/transactions.py`.
- Output formatting: aligned columns with localized numbers.

## Test Guide

- Each filter narrows the result set correctly.
- Empty result returns an empty table with a "no transactions" message.
- Multiple filters compose with AND semantics.
- `--description <substring>` is case-insensitive and partial.
