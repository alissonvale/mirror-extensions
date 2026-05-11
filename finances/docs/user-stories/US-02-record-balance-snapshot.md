[< User Stories](README.md)

# US-02 — Record balance snapshot

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user reconciling my real account balances against what the
extension thinks I have,
**I want** to record a point-in-time balance for any account
(typed manually or imported from a statement),
**so that** the `balance` and `runway` commands work from authoritative
numbers, not from a running sum that drifts as transactions are
amended.

Snapshots are append-only. The latest snapshot for an account is the
current balance.

### Acceptance value

- `python -m memory ext finances snapshot <account_id> <date> <balance> [--source manual|ofx|reconciliation]`
- `python -m memory ext finances balance` lists the latest snapshot
  per account.
- `python -m memory ext finances balance <account_id>` returns a single
  value.

## Plan

- Model `BalanceSnapshot`.
- Store: `create_snapshot`, `get_latest_snapshot(account_id)`,
  `list_snapshots(account_id, start_date, end_date)`.
- CLI handlers in `src/cli/balance.py`.
- US-01's `add_account` already creates the `source='opening'`
  snapshot; this story does not need to backfill anything.

## Test Guide

- Snapshot insert succeeds; reading back returns it.
- Multiple snapshots per account allowed; `get_latest_snapshot` returns
  the highest `date` (ties broken by `created_at`).
- `--source` defaults to `manual` and accepts the documented values.
