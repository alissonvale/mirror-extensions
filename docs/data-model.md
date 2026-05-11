[< finances](../README.md)

# Data model

Five tables, all under the `ext_finances_*` prefix. Defined in
[`migrations/001_init.sql`](../migrations/001_init.sql). The shape is
copied 1:1 from the legacy `eco_*` schema so [US-11](user-stories/US-11-migrate-legacy-data.md)
can do a pure copy migration.

## `ext_finances_accounts`

An identifiable place where money lives.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. 8-char hex from `uuid4().hex[:8]`. |
| `name` | TEXT | no | — | Human-friendly name (e.g. `Itaú PF`, `Nubank RDB`). |
| `bank` | TEXT | yes | — | Bank name. |
| `agency` | TEXT | yes | — | Branch number. |
| `account_number` | TEXT | yes | — | Masked or last-N digits; used for auto-match in importers. |
| `type` | TEXT | no | — | `checking` \| `credit_card` \| `savings`. |
| `entity` | TEXT | no | — | `personal` \| `business`. |
| `liquidity` | TEXT | no | `'liquid'` | `liquid` \| `semi_liquid` \| `illiquid`. Drives runway scope. |
| `opening_balance` | REAL | no | `0` | Balance at `opening_date`. |
| `opening_date` | TEXT | no | — | ISO date. |
| `created_at` | TEXT | no | — | ISO datetime. |
| `metadata` | TEXT | yes | — | Reserved for extension-internal use (JSON when set). |

## `ext_finances_categories`

User-defined buckets for transactions (groceries, software, etc.).

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. |
| `name` | TEXT | no | — | UNIQUE. |
| `type` | TEXT | no | — | `income` \| `expense` \| `transfer`. |
| `created_at` | TEXT | no | — | ISO datetime. |

In production the legacy table was empty; this extension keeps the
shape for parity with [US-09](user-stories/US-09-categorize-transactions.md).

## `ext_finances_transactions`

A single line item in any account's history.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. |
| `account_id` | TEXT | no | — | FK → `ext_finances_accounts(id)`. |
| `date` | TEXT | no | — | ISO date. |
| `description` | TEXT | no | — | What the bank printed. |
| `memo` | TEXT | yes | — | Free-form note (often equal to description). |
| `amount` | REAL | no | — | Positive = credit, negative = debit. |
| `type` | TEXT | no | — | `credit` \| `debit`. Mirrors the sign of `amount`. |
| `category_id` | TEXT | yes | — | FK → `ext_finances_categories(id)`. |
| `fit_id` | TEXT | yes | — | Bank-side transaction id; used for deduplication on re-imports. |
| `balance_after` | REAL | yes | — | Reported running balance, when the source provides it. |
| `created_at` | TEXT | no | — | ISO datetime. |
| `metadata` | TEXT | yes | — | JSON, optional. |

Indices: `account_id`, `date`, `fit_id`, `category_id`.

## `ext_finances_balance_snapshots`

Point-in-time balance for an account. Append-only.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. |
| `account_id` | TEXT | no | — | FK → `ext_finances_accounts(id)`. |
| `date` | TEXT | no | — | ISO date. |
| `balance` | REAL | no | — | Account balance on `date`. |
| `source` | TEXT | no | `'manual'` | `manual` \| `ofx` \| `opening` \| `reconciliation`. |
| `created_at` | TEXT | no | — | ISO datetime. |

Indices: `account_id`, `date`. The latest snapshot per account is the
current balance.

## `ext_finances_recurring_bills`

Forward-looking commitments (rent, subscriptions, insurance).

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. |
| `name` | TEXT | no | — | Human name. |
| `entity` | TEXT | no | — | `personal` \| `business`. |
| `category` | TEXT | no | — | `fixed` \| `variable`. **Not** a FK to `categories` — this column tracks volatility, not topic. |
| `amount` | REAL | no | — | Monthly value. Negative by convention for expenses. |
| `day_of_month` | INTEGER | yes | — | Day the charge typically lands. |
| `notes` | TEXT | yes | — | Free-form. |
| `active` | INTEGER | no | `1` | `0` removes the bill from runway calculations without deleting it. |
| `created_at` | TEXT | no | — | ISO datetime. |

## Invariants

These hold across all five tables and are the contract a future reader
should be able to trust:

- Every `transactions.account_id` resolves to an `accounts.id`.
- Every `balance_snapshots.account_id` resolves to an `accounts.id`.
- `transactions.category_id`, when not NULL, resolves to a
  `categories.id`.
- `transactions.amount` and `transactions.type` agree on sign:
  `amount >= 0 ↔ type = 'credit'`.
- For every account, at least one `opening`-source snapshot exists
  on `opening_date`. This is created automatically by
  [US-01](user-stories/US-01-register-and-list-accounts.md).
- `recurring_bills.amount` is negative for expense rows (the report
  helper sums without sign-flipping).
- IDs are stable strings. The migration in
  [US-11](user-stories/US-11-migrate-legacy-data.md) preserves the
  legacy IDs verbatim so historic references in memories or journal
  entries still resolve.
