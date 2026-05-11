[< User Stories](README.md)

# US-06 — Manage recurring bills

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user with fixed monthly costs (rent, subscriptions, insurance),
**I want** to keep a registry of those bills with name, amount, day of
month, and active/inactive flag,
**so that** the runway calculation in [US-07](US-07-calculate-burn-and-runway.md)
has an authoritative monthly burn that does not require parsing past
transactions.

A bill is **forward-looking**: it represents commitment, not history.
A bill that is inactivated is preserved (audit trail) but excluded
from the burn calculation.

### Acceptance value

- `python -m memory ext finances bills` — list all active bills with
  totals by entity (personal vs business).
- `python -m memory ext finances bills add --name "..." --entity personal --category fixed --amount 1200 [--day-of-month 5] [--notes "..."]`
- `python -m memory ext finances bills remove <id>` — inactivates
  (does not delete).
- `python -m memory ext finances bills --include-inactive` — show the
  full registry.

## Plan

- Model `RecurringBill`.
- Store: `create_bill`, `list_bills(active=True)`, `deactivate_bill`,
  `get_bill`.
- CLI handler in `src/cli/bills.py`.
- Amount is stored negative for expenses by convention so the runway
  helper can sum without sign-flipping.

## Test Guide

- `add` persists with `active=1`.
- `remove` toggles `active=0` and the row remains.
- `--include-inactive` widens the listing.
- Totals by entity respect the active flag.
