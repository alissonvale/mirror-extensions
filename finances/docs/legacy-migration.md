[< finances](../README.md)

# Legacy migration

This document is the user-facing procedure for the work specified in
[US-11](user-stories/US-11-migrate-legacy-data.md). It describes how
to move a complete financial data set from a legacy mirror SQLite
database that carries the `eco_*` schema into this extension's tables
under the active mirror.

Throughout this document `<legacy-db-path>` is the path to that
legacy file on your machine.

## Scope

Migrated:

- `eco_accounts` → `ext_finances_accounts`
- `eco_categories` → `ext_finances_categories`
- `eco_balance_snapshots` → `ext_finances_balance_snapshots`
- `eco_transactions` → `ext_finances_transactions`
- `eco_recurring_bills` → `ext_finances_recurring_bills`

Not migrated (out of scope for this extension):

- conversations, memories, journeys, attachments, testimonials, llm
  calls. Those belong to the mirror core or to other extensions and
  have their own migration paths.

## Prerequisites

- The finances extension is installed:
  `python -m memory extensions install finances --extensions-root <path>`.
- The active mirror home is configured via `MIRROR_HOME` or
  `MIRROR_USER`.
- The legacy database file exists and is readable at the path you
  intend to pass as `--source`. The migration opens it in read-only
  mode; nothing in the legacy database is modified.
- It is a good idea to back up the active mirror database before
  running the real migration:
  `python -m memory backup` (or copy `<mirror_home>/memory.db`
  manually).

## Dry run

Always run dry first:

```bash
python -m memory ext finances migrate-legacy \
  --source <legacy-db-path> \
  --dry-run
```

Expected output (counts depend on your legacy data set):

```
Dry run — no changes will be written.

  ext_finances_accounts             N would be imported
  ext_finances_categories           N would be imported
  ext_finances_balance_snapshots    N would be imported
  ext_finances_transactions         N would be imported
  ext_finances_recurring_bills      N would be imported

Total: N rows would be imported.
```

If the numbers do not look right, **stop**. Re-run the dry-run after
investigating; do not apply.

## Apply

```bash
python -m memory ext finances migrate-legacy \
  --source <legacy-db-path>
```

The output matches the dry-run but with `imported` in place of
`would be imported`. The migration runs inside a single savepoint;
either every row lands or none does.

## Verification

After a successful apply:

```bash
# Counts should match the dry-run.
python -m memory ext finances migrate-legacy \
  --source <legacy-db-path> \
  --dry-run
# expected: every table reports 0 would be imported.
```

Spot-check a few rows directly:

```bash
sqlite3 ~/.mirror/<user>/memory.db \
  "SELECT COUNT(*), MIN(date), MAX(date) FROM ext_finances_transactions;"
```

## Idempotence

Re-running the apply imports zero rows. The migration deduplicates by
primary key (`id`) per table, so even partial state is recoverable:
delete the unwanted rows manually, re-run, the migration tops up the
rest.

## Rollback

There is no built-in rollback because the migration is purely
additive. Two options:

- **Targeted:** delete the rows the migration inserted from each
  `ext_finances_*` table. The legacy database is untouched, so you
  can re-run after fixing whatever went wrong.
- **Full reset:** uninstall and reinstall the extension. Per the
  framework contract, `python -m memory extensions uninstall
  finances` sweeps the binding rows but **preserves the
  `ext_finances_*` data tables**. To wipe data, drop the tables
  manually:
  ```sql
  DROP TABLE ext_finances_recurring_bills;
  DROP TABLE ext_finances_transactions;
  DROP TABLE ext_finances_balance_snapshots;
  DROP TABLE ext_finances_categories;
  DROP TABLE ext_finances_accounts;
  DELETE FROM _ext_migrations WHERE extension_id = 'finances';
  ```
  Then re-install the extension and re-run the migration.

## Invariants preserved

- IDs are copied verbatim. Any external artifact that referenced an
  account or transaction by id (memories, journal entries, etc.) still
  resolves after the migration.
- The `liquidity` column on accounts is preserved as recorded in the
  legacy database; no defaults are re-applied to existing rows.
- `transactions.category_id` stays `NULL` where it was `NULL`. The
  legacy categories table is typically empty; the migration does not
  invent categories.

## Invariants intentionally broken

None at the data level. The only thing that changes between legacy
and new is the table prefix. The migration is, by design, a copy.
