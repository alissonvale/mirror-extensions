[< testimonials](../README.md)

# Commands

Four CLI subcommands under `python -m memory ext testimonials`.

## `add`

Register a testimonial from free text. The LLM extracts the structured
fields.

```
python -m memory ext testimonials add "<free text>"
```

The text is the user's description of the testimonial. The LLM extracts:

- `author_name` — the person who wrote it (default: `Anonymous`)
- `content` — the verbatim quote
- `source` — channel (whatsapp / email / linkedin / etc.)
- `product` — the product or service the testimonial refers to
- `highlight` — a one-sentence quotable extract
- `tags` — 2–5 thematic tags useful for search
- `received_at` — ISO date when the testimonial arrived

The extracted fields are echoed back. The `content` is embedded and
stored for semantic search.

Failure modes:
- LLM fails → a fallback record is saved (author = `Anonymous`,
  content = the raw input, no structured fields). A warning prints;
  the row still exists and can be edited later.
- Embedding fails → the record is saved without an embedding; it
  will not appear in `search` but `list` still works.

## `list`

```
python -m memory ext testimonials list [--product <name>] [--author <substring>] [--source <channel>]
```

Filters compose with AND. Output is ordered by `received_at` then
`created_at`, both descending. Each row shows: id, author, source,
received date, product, highlight (or the first 120 chars of content
if no highlight), and tags.

## `search`

```
python -m memory ext testimonials search "<query>" [--limit <N>]
```

Embeds the query and ranks every testimonial with a non-null
embedding by cosine similarity. Default limit is 5.

The query is natural language; semantic search handles paraphrase
and language drift better than substring matches. Identical content
yields a score of `1.0`; unrelated content yields near-zero scores.

## `migrate-legacy`

```
python -m memory ext testimonials migrate-legacy --source <path> [--dry-run]
```

Imports every row from a legacy mirror SQLite database's
`testimonials` table into `ext_testimonials_records`. Embeddings are
copied verbatim — the legacy mirror used the same embedding model as
the framework's `api.embed()` does today.

`--dry-run` reports the counts that would be imported without
writing anything. Idempotent: re-runs after a successful migration
import zero rows.

See [legacy-migration.md](legacy-migration.md) for the full procedure.
