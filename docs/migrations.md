[< finances](../README.md)

# Migrations

Chronological list of SQL migration files. The list is the canonical
history; the SQL files in `migrations/` are the implementation.

| File | Date | Summary |
|---|---|---|
| [`001_init.sql`](../migrations/001_init.sql) | 2026-05-11 | Initial schema. Defines `ext_finances_accounts`, `ext_finances_categories`, `ext_finances_transactions`, `ext_finances_balance_snapshots`, `ext_finances_recurring_bills` plus indices. |

## 001_init

**Why.** The extension is starting from scratch but must receive a
legacy data set (see [US-11](user-stories/US-11-migrate-legacy-data.md))
without column transformations. The schema is therefore a 1:1 copy of
the legacy `eco_*` shape with the table prefix changed.

**What changed.** Five tables and seven indices, all under the
`ext_finances_*` prefix.

**Backfill.** None at the migration level. The legacy data is imported
through the `migrate-legacy` CLI subcommand (US-11), not through SQL.

**Compatibility.** None to break — this is the first migration.

## Schema versioning

`ext_finances_*` does not yet carry a meta table for schema version.
If future migrations introduce breaking shape changes (e.g. splitting
`transactions.metadata` into typed columns), a `ext_finances_meta`
single-row table will be added at that point, following the convention
in
[Mirror Mind / Extensions / migrations](../../../mirror/docs/product/extensions/migrations.md#schema-versioning-beyond-migrations).
