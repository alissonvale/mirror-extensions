[< testimonials](../README.md)

# Migrations

| File | Date | Summary |
|---|---|---|
| [`001_init.sql`](../migrations/001_init.sql) | 2026-05-11 | Initial schema. Defines `ext_testimonials_records` plus indices on `product` and `received_at`. |

## 001_init

**Why.** The extension is starting from scratch but must receive a
legacy data set (see [US-04](user-stories/US-04-migrate-legacy-testimonials.md))
without column transformations. The schema is therefore a column-for-
column copy of the legacy `testimonials` table, with the prefix
changed to `ext_testimonials_`.

**What changed.** One table (`ext_testimonials_records`), two
indices (`product`, `received_at`).

**Backfill.** None at the migration level. Legacy data is imported
through `migrate-legacy`, not through SQL.

**Compatibility.** First migration; nothing to break.
