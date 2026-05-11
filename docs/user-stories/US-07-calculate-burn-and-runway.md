[< User Stories](README.md)

# US-07 — Calculate burn and runway

**Status:** ⚪ Planned

## Story

**As a** user living off reserves while building something new,
**I want** to know how many months my money lasts at the current
spending rate,
**so that** every financial decision is grounded in time, not in
abstract numbers.

Two burn sources are supported:

- `bills` — the sum of active recurring bills from
  [US-06](US-06-manage-recurring-bills.md). Forward-looking; reflects
  commitments.
- `history` — the average monthly outflow over the last three months
  of transactions. Backward-looking; reflects actual behavior.

The user picks the source. Runway = consolidated balance ÷ |burn|.

### Acceptance value

- `python -m memory ext finances runway [--include-liquidity liquid,semi_liquid] [--burn-source bills|history] [--lookback-months 3]`
- Output: balance summary by liquidity bucket, monthly burn from the
  chosen source (with the alternative computed for comparison), runway
  in months, "how much longer until X date" when the answer is finite.

## Plan

- `src/reports.py`:
  - `consolidated_balance(accounts, snapshots, liquidity_filter)` ->
    `{liquid, semi_liquid, illiquid, total}`.
  - `monthly_burn_from_bills(conn) -> float | None`.
  - `monthly_burn_from_history(transactions, lookback_months) -> float`.
  - `runway(balance, burn) -> float | None`.
- CLI handler in `src/cli/runway.py` composes the helpers.

## Test Guide

- Empty database: balance 0, burn `None`, runway `None`.
- Bills source ignored when no bills exist; falls back to history with
  a message.
- History source over <3 months falls back to whatever exists with a
  message.
- `--include-liquidity` widens the included accounts; numbers move
  predictably.
- Runway is finite even when burn is exactly 0 (returns `inf` or a
  textual "indefinite"; pick one and document it).
