[< testimonials](../README.md)

# Architecture

```
testimonials/
├── extension.py               -- register(api): 4 CLI subcommands
├── skill.yaml                 -- manifest (kind: command-skill)
├── SKILL.md                   -- agent-facing skill
├── migrations/
│   └── 001_init.sql           -- one table + two indices
├── src/
│   ├── models.py              -- Testimonial dataclass + tag codec
│   ├── store.py               -- read helpers
│   ├── store_writes.py        -- insert helpers
│   ├── parse.py               -- LLM-driven free-text extractor
│   ├── search.py              -- cosine similarity + ranking
│   ├── migrate_legacy.py      -- legacy SQLite copier
│   └── cli/
│       ├── add.py             -- US-01
│       ├── list.py            -- US-02
│       ├── search.py          -- US-03
│       └── migrate_legacy.py  -- US-04
├── tests/                     -- 39 tests, all green
└── docs/
```

## Read/write split

`store.py` reads, `store_writes.py` writes. Both go through the
framework's `ExtensionAPI`, which prefix-enforces every write against
`ext_testimonials_*`. The read path is allowed to touch any table
(framework contract), but this extension only reads its own.

## LLM extraction (`src/parse.py`)

`parse_testimonial(api, text)` sends the user's free-text input to
the LLM router with a JSON-only prompt template. Behaviour:

- LLM returns clean JSON → fields land.
- LLM wraps the JSON in code fences → fences are stripped.
- LLM raises (network down, rate limit, etc.) → fallback record is
  built from the raw text. Author is `Anonymous`, content is the
  user's input, no tags, today as received date. A warning is logged
  via `api.log()`.
- LLM returns garbage → same fallback path, with a different warning.

This design treats the LLM as enrichment, not as a hard dependency.
A user can always save a testimonial even if the LLM is unavailable.

## Embeddings (`src/search.py`)

`api.embed(text)` returns a 1536-dim float32 vector serialised as
6144 bytes. We store that BLOB on each row and search by cosine
similarity in pure Python (numpy). The choice not to use SQLite's
own vector extension keeps this extension portable to any vanilla
SQLite build.

`cosine_similarity` is defensive against shape drift: empty bytes,
zero norms, and dimensionality mismatch all return 0.0 instead of
raising. This matters because legacy data may carry vectors from a
different (or differently-versioned) model; a 0.0 score buries those
rows at the bottom rather than crashing the search.

## Legacy migration (`src/migrate_legacy.py`)

Same shape as the finances legacy migration: read-only URI ATTACH,
validate that the `testimonials` table exists, copy missing rows
inside a single `api.transaction()` savepoint. Embeddings are passed
through verbatim — no re-embedding, no transformation.

## Why no Mirror Mode context provider?

Testimonials are queried, not always shown. Injecting a "recent
testimonials" block into every Mirror Mode turn would pollute most
conversations.

A future capability could expose targeted testimonials (e.g. the top
3 hits for the active journey's name) for personas working on
copy/launch. That story is deliberately not scoped yet.
