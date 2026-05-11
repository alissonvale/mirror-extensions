[< User Stories](README.md)

# US-11 — Migrate legacy data

**Status:** ✅ Done · 2026-05-11

## Story

**As a** user who carries years of financial data in a legacy mirror
SQLite database that uses the `eco_*` schema,
**I want** a single command that copies every legacy account,
transaction, balance snapshot, and recurring bill into this
extension's tables,
**so that** the move to the current mirror does not cost me history,
and so that every other story in this extension can be exercised
against real data from day one.

The legacy schema and this extension's schema were designed to be
**isomorphic at the column level**: the only thing that moves is the
table prefix (`eco_` → `ext_finances_`). No type changes, no column
renames, no derived fields. That is a deliberate choice. The
migration must be a copy, not an interpretation.

### Acceptance value

- `python -m memory ext finances migrate-legacy --source <legacy-db-path> [--dry-run]`
- Dry-run reports the count it **would** import per table.
- Real run imports and reports the count it **did** import per table.
- Idempotent: re-running imports 0 rows.
- After a successful real run, the user's mirror database contains the
  full legacy data set under the new prefix, ready for every other
  story.

### Why this story runs first

The other ten stories define capabilities that operate on a schema.
Without legacy data, those capabilities have nothing real to operate
on — every test would be hand-crafted fixtures, and the schema would
risk drifting from what 554 real transactions actually look like.
Migrating first means:

- the schema is validated against production-shape data;
- every other story is exercised against real numbers from the first
  test run;
- the user's day-one experience after this story is "my finances are
  here", not "the extension exists but is empty".

## Plan

### Files to add

```
src/migrate_legacy.py             # the orchestrator and table-by-table copiers
src/cli/migrate_legacy.py         # CLI handler registered as 'migrate-legacy'
tests/test_migrate_legacy.py      # unit tests on a synthetic legacy db
tests/fixtures/legacy_seed.sql    # a small representative legacy database
docs/legacy-migration.md          # the user-facing procedure (already templated)
```

### Migration shape

The orchestrator opens the legacy database with `ATTACH DATABASE`
under the alias `legacy` and runs one `INSERT INTO ext_finances_<t>
SELECT ... FROM legacy.eco_<t> WHERE id NOT IN (SELECT id FROM
ext_finances_<t>)` per table. Order matters because of FK references:

1. `eco_accounts`        → `ext_finances_accounts`
2. `eco_categories`      → `ext_finances_categories`
3. `eco_balance_snapshots` → `ext_finances_balance_snapshots`
4. `eco_transactions`    → `ext_finances_transactions`
5. `eco_recurring_bills` → `ext_finances_recurring_bills`

All five run inside one savepoint. If any one fails (e.g. an FK that
does not resolve), the whole migration rolls back. The user can fix
the source and re-run.

The legacy schema has one column the new schema does not need to add:
`eco_accounts.liquidity` was introduced via a migration in the legacy
project. The new schema ships with `liquidity` from `001_init.sql`
already, so the column maps 1:1. No backfill needed.

The new schema also accepts the same `id` values (TEXT, 8-char hex
from `uuid4().hex[:8]` in the legacy code). Preserving the ids means
memories, conversations, journal entries, and any other artifact that
ever referenced an account or transaction by id continues to resolve.

### Idempotence

Each `INSERT ... SELECT` filters with `WHERE id NOT IN (SELECT id
FROM ext_finances_<t>)`. Re-running after a successful migration
adds zero rows. The user can also delete partial state manually and
re-run; the savepoint ensures no half-migrations.

### Dry-run

`--dry-run` runs each `SELECT count(*) FROM legacy.eco_<t> WHERE id
NOT IN (SELECT id FROM ext_finances_<t>)` and prints the would-be
count per table without writing. Exits with `0`.

### Safety

The orchestrator never **deletes** anything in the legacy database.
It does not even open the legacy file in read-write mode (uses
`ATTACH DATABASE '<path>' AS legacy` which defaults to read-only when
the file is on disk; we make it explicit by opening the legacy file
with a `mode=ro` URI).

### CLI argument shape

```
python -m memory ext finances migrate-legacy --source <path> [--dry-run]
```

- `--source` required.
- `--dry-run` optional.

### Output shape

Real run:

```
Migrating from <legacy-db-path> ...

  ext_finances_accounts             N imported, 0 skipped
  ext_finances_categories           N imported, 0 skipped
  ext_finances_balance_snapshots    N imported, 0 skipped
  ext_finances_transactions         N imported, 0 skipped
  ext_finances_recurring_bills      N imported, 0 skipped

Total: N rows imported.
```

Dry-run:

```
Dry run — no changes will be written.

  ext_finances_accounts            18 would be imported
  ...

Total: 681 rows would be imported.
```

## Test Guide

### Cases

- **Synthetic legacy fixture** (`tests/fixtures/legacy_seed.sql`):
  builds a small legacy database (3 accounts, 5 transactions, 2
  snapshots, 1 recurring bill) with the legacy schema. Tests run
  against it, never against any real legacy database.

- **Happy path:**
  - Migration imports the expected counts per table.
  - Every row's column values match the source row exactly.
  - Foreign keys (`transactions.account_id`, `snapshots.account_id`,
    `transactions.category_id`) all resolve in the new tables.

- **Idempotence:**
  - Migration twice in a row: second run imports 0 rows.
  - Migration after deleting a single row: only the missing row is
    re-imported.

- **Dry-run:**
  - Reports the same counts the real run would import.
  - Does not write to `_ext_migrations` or any `ext_finances_*` table.
  - Exits 0.

- **Failure modes:**
  - `--source` path does not exist: clean error, exit 1.
  - `--source` path is not a SQLite database: clean error, exit 1.
  - Legacy database missing one of the expected tables: clean error
    naming the missing table.
  - A legacy row with an orphan FK (transaction pointing to a
    non-existent account) aborts the whole migration; the database is
    left untouched.

- **Cross-schema invariant:**
  - The new schema has the column `liquidity` on `accounts`. Legacy
    rows always have it (post the legacy ALTER TABLE). The migration
    must not silently drop or remap it.
  - The new schema has `category_id` as a nullable FK. Legacy
    `category_id` is mostly `NULL` (the legacy categories table is
    empty in production); the migration preserves `NULL` and does not
    invent values.

### Smoke test against real legacy data

After implementation, the developer runs:

```
python -m memory ext finances migrate-legacy --source <legacy-db-path> --dry-run
```

against their real legacy file and confirms the counts match the
row counts in the source database. Then runs the real migration and
confirms a follow-up dry-run reports zero pending rows.

### Done criteria

- [ ] `migrate-legacy --dry-run` reports correct counts against the
      synthetic fixture.
- [ ] Real migration against the fixture passes every test above.
- [ ] Smoke test against a real legacy database matches expected
      counts.
- [ ] Re-run after success imports zero rows.
- [ ] `docs/legacy-migration.md` describes the procedure end to end
      with a worked example.
- [ ] No code path opens the legacy database in read-write mode.
