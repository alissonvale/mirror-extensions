[< User Stories](README.md)

# US-09 — Categorize transactions

**Status:** ⚪ Planned

## Story

**As a** user trying to see where my money actually goes,
**I want** to tag transactions with categories (groceries, transport,
software, etc.) and read reports broken down by category,
**so that** patterns hidden in raw line items become visible.

Categories are user-defined. The schema already supports them
(`ext_finances_categories` + `transactions.category_id` foreign key);
this story adds the CRUD and the categorization workflow.

### Acceptance value

- `python -m memory ext finances categories [add <name> <type> | list | remove <id>]`
  where `type` is `income | expense | transfer`.
- `python -m memory ext finances categorize <transaction-id> <category-id-or-name>`
  attaches the category to the transaction.
- The monthly report from [US-08](US-08-monthly-cash-flow-report.md)
  gains a `--by-category` flag.

## Plan

- Model `Category`.
- Store: `create_category`, `get_category_by_name`,
  `get_or_create_category`, `list_categories`, `set_transaction_category`.
- CLI handlers in `src/cli/categories.py` and
  `src/cli/categorize.py`.
- Report update in `src/reports.py`:
  `summarize_by_category(transactions) -> dict[category, dict]`.

## Test Guide

- `categories add` persists; duplicate name (case-insensitive) is a
  no-op returning the existing id.
- `categorize` accepts either an id or a name (resolves the name
  internally).
- Report `--by-category` produces a row per category sorted by total.
- Uncategorized transactions roll up under `(uncategorized)`.
