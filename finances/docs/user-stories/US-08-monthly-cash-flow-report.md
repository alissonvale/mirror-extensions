[< User Stories](README.md)

# US-08 — Monthly cash flow report

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user reviewing my finances at the end of each month,
**I want** a deterministic summary of income, expense, and net flow
per month,
**so that** trends become visible without manual aggregation.

### Acceptance value

- `python -m memory ext finances report [--account <id>] [--from <date>] [--to <date>]`
- Output: a row per month with `YYYY-MM`, income (positive
  transactions), expense (sum of negatives, displayed positive), net.
- Totals row at the bottom over the requested range.

## Plan

- `src/reports.py`:
  - `summarize_by_month(transactions, *, account_id=None, start_date=None, end_date=None) -> dict[str, dict]`.
- CLI handler in `src/cli/report.py`.
- Output formatting: aligned columns; `--json` for machine consumption.

## Test Guide

- Empty database: empty report with a "no transactions" message.
- Single account / all accounts produce different but predictable
  numbers.
- Date range filters apply correctly.
- Sign convention: income positive, expense displayed positive but
  derived from negative amounts.
