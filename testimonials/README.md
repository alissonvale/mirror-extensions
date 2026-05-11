# testimonials

A Mirror Mind extension for archiving customer testimonials with
LLM-assisted structuring and semantic search.

This is a **`command-skill` extension**. It owns the
`ext_testimonials_records` table in the shared mirror database,
exposes a CLI under `python -m memory ext testimonials`, and pairs
naturally with personas focused on writing, marketing, and customer
communication.

## Install

```bash
python -m memory extensions install testimonials \
  --extensions-root ~/Code/mirror-extensions
```

The mirror home is read from `MIRROR_HOME` / `MIRROR_USER`.

## Top commands

```bash
python -m memory ext testimonials add "Pedro on WhatsApp: 'Loved the workshop.'"
python -m memory ext testimonials list [--product <name>]
python -m memory ext testimonials search "<natural-language query>"
python -m memory ext testimonials migrate-legacy --source <legacy-db-path>
```

Full reference in [docs/commands.md](docs/commands.md).

## What sets it apart

- **`add` accepts free text.** The CLI invokes the framework's LLM
  router to extract `author_name`, the verbatim `content`, the
  channel (`source`), the `product`, a quotable `highlight`, and 2–5
  `tags`. The user does not have to type structured data.
- **Search is semantic.** Each testimonial's content is embedded
  with the framework's `api.embed()` and stored as a BLOB. Queries
  are embedded the same way and ranked by cosine similarity —
  paraphrase and language drift do not hide relevant matches.
- **Legacy embeddings are reused.** The legacy mirror used the same
  embedding model (`text-embedding-3-small`); `migrate-legacy`
  copies the precomputed vectors verbatim so the archive is
  immediately searchable after the import.

## Documentation

- [Architecture](docs/architecture.md)
- [Commands](docs/commands.md)
- [Data model](docs/data-model.md)
- [Migrations](docs/migrations.md)
- [Legacy migration](docs/legacy-migration.md)
- [User stories](docs/user-stories/README.md)
- [Changelog](docs/CHANGELOG.md)

## Status

✅ Complete (4/4 stories).
