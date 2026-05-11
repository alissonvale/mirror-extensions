[< testimonials](../README.md)

# Legacy migration

This document is the operator-facing procedure for the work specified
in [US-04](user-stories/US-04-migrate-legacy-testimonials.md). It
moves every row from a legacy mirror SQLite database's `testimonials`
table into this extension's `ext_testimonials_records` table.

`<legacy-db-path>` throughout this document is the path to the legacy
file on your machine (e.g. a previous mirror installation's
`memoria.db`).

## Scope

Migrated:

- every row from the legacy `testimonials` table.
- every column verbatim, **including the embedding BLOB**. The
  legacy mirror used the same embedding model
  (`text-embedding-3-small`) the framework's `api.embed()` uses
  today, so the precomputed vectors stay valid for semantic search.

Not migrated (out of scope): conversations, memories, journeys,
attachments, finance data. Those belong to the mirror core or to
other extensions.

## Prerequisites

- The testimonials extension is installed:
  `python -m memory extensions install testimonials --extensions-root <path>`.
- The active mirror home is configured (`MIRROR_HOME` / `MIRROR_USER`).
- The legacy database file exists and is readable. The migration
  opens it in read-only URI mode; nothing in the source is modified.
- It is a good idea to back up the active mirror database first:
  `python -m memory backup`.

## Dry run

```bash
python -m memory ext testimonials migrate-legacy \
  --source <legacy-db-path> \
  --dry-run
```

The output reports the count that would be imported and the count
that would be skipped (rows already present in the destination). If
the count looks wrong, **stop** — investigate before applying.

## Apply

```bash
python -m memory ext testimonials migrate-legacy --source <legacy-db-path>
```

Runs inside a single `api.transaction()` savepoint: either every
missing row lands or none does.

## Verification

```bash
# Counts should match the dry-run on the first apply.
python -m memory ext testimonials migrate-legacy \
  --source <legacy-db-path> \
  --dry-run
# Expected after a successful apply: 0 would be imported.

python -m memory ext testimonials list
python -m memory ext testimonials search "<a query you expect to match>"
```

## Idempotence

Re-running the apply imports zero rows. The migration dedupes by
primary key (`id`); partial states are topped up cleanly (delete the
unwanted rows manually and re-run).

## Rollback

The migration is purely additive. Two options:

- **Targeted:** delete the rows the migration inserted. The legacy
  database is untouched; re-run after fixing whatever went wrong.
- **Full reset:** drop the extension's tables manually and re-install:
  ```sql
  DROP TABLE ext_testimonials_records;
  DELETE FROM _ext_migrations WHERE extension_id = 'testimonials';
  ```
  Then `python -m memory extensions install testimonials --extensions-root <path>`
  and re-run the migration. Per the framework contract,
  `extensions uninstall` sweeps the binding rows but
  **preserves the `ext_testimonials_*` data tables**; manual drop is
  the only way to wipe data.
