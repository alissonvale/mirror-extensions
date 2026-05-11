# finances

A Mirror Mind extension that tracks personal and business cash flow:
accounts (checking, credit card, savings, investments), transactions,
periodic balance snapshots, and recurring bills. Computes monthly burn
rate and runway. Surfaces a live financial summary to Mirror Mode
when bound to a financially-aware persona.

This is a **`command-skill` extension**. It owns a set of SQLite
tables under the `ext_finances_*` prefix in the shared mirror
database, exposes a CLI under `python -m memory ext finances`, and
optionally provides Mirror Mode context. See
[Mirror Mind / Extensions](../../mirror/docs/product/extensions/index.md)
for the system that hosts it.

## Install

```bash
python -m memory extensions install finances \
  --extensions-root ~/Code/mirror-extensions
```

The mirror home is read from `MIRROR_HOME` / `MIRROR_USER` in the
active environment.

## Top commands

```bash
python -m memory ext finances accounts            # list all accounts
python -m memory ext finances balance             # current balance per account
python -m memory ext finances runway              # liquid balance / monthly burn
python -m memory ext finances report              # monthly income / expense / net
python -m memory ext finances migrate-legacy --source <legacy-db-path>
```

Full reference in [docs/commands.md](docs/commands.md).

## Mirror Mode integration

```bash
python -m memory ext finances bind financial_summary --persona treasurer
```

Any Mirror Mode turn that routes to the bound persona now includes a
live financial summary in the prompt under
`=== extension/finances/financial_summary ===`. See
[docs/bindings.md](docs/bindings.md) for the full binding workflow and
[docs/persona-recipes.md](docs/persona-recipes.md) for suggested
persona briefings.

## Documentation

- [Architecture](docs/architecture.md) — internal modules and data
  flow.
- [Commands](docs/commands.md) — full CLI reference.
- [Data model](docs/data-model.md) — every table this extension owns.
- [Bindings](docs/bindings.md) — the `financial_summary` capability.
- [Migrations](docs/migrations.md) — schema evolution history.
- [Legacy migration](docs/legacy-migration.md) — how to import data
  from a legacy mirror SQLite database that carries the `eco_*`
  schema.
- [Persona recipes](docs/persona-recipes.md) — suggested briefings.
- [User stories](docs/user-stories/README.md) — the road that brought
  this extension to its current shape.
- [Changelog](docs/CHANGELOG.md).

## Status

🟡 Under construction. The schema is defined; the `migrate-legacy`
subcommand is the next milestone (see
[US-11](docs/user-stories/US-11-migrate-legacy-data.md)).
