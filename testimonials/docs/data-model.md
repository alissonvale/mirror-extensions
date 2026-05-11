[< testimonials](../README.md)

# Data model

One table, under the `ext_testimonials_*` prefix. Defined in
[`migrations/001_init.sql`](../migrations/001_init.sql).

## `ext_testimonials_records`

A single customer testimonial — structured fields plus the original
content and an embedding for semantic search.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | TEXT | no | — | PRIMARY KEY. 8-char hex from `uuid4().hex[:8]`. Preserved verbatim across the legacy migration. |
| `author_name` | TEXT | no | — | The person who wrote the testimonial. `Anonymous` when unknown. |
| `content` | TEXT | no | — | The testimonial itself, verbatim. The customer's voice, not a paraphrase. |
| `source` | TEXT | yes | — | Channel: `whatsapp` / `email` / `linkedin` / `live` / `instagram` / `youtube` / `telegram` / `form` / `sms` / `in-person` / `other` / etc. Free-form; not enforced at the schema level. |
| `product` | TEXT | yes | — | The product/service the testimonial refers to. Free-form. Indexed for `list --product`. |
| `highlight` | TEXT | yes | — | A one-sentence quotable extract from `content`. Extracted by the LLM at `add` time. |
| `tags` | TEXT | yes | — | JSON-encoded list of strings. Decoded into a tuple at read time. |
| `received_at` | TEXT | yes | — | ISO date when the testimonial was received. Indexed for ordering. |
| `created_at` | TEXT | no | — | ISO datetime the row was inserted into this extension. |
| `embedding` | BLOB | yes | — | float32 vector matching `api.embed()` output (1536 dims = 6144 bytes for OpenAI `text-embedding-3-small`). NULL means the row will not appear in semantic search. |

## Indices

- `idx_ext_testimonials_records_product` — speeds up the `--product`
  filter in `list`.
- `idx_ext_testimonials_records_received` — speeds up ordering by
  `received_at DESC`.

## Invariants

- IDs are stable strings. The migration in
  [US-04](user-stories/US-04-migrate-legacy-testimonials.md)
  preserves the legacy IDs verbatim.
- `embedding`, when set, has exactly `1536 * 4 = 6144` bytes. The
  migration accepts whatever shape the source ships; the search code
  is defensive against dimensionality drift (returns 0.0 score
  rather than raising).
- `content` is the customer's verbatim words. The CLI's `add`
  subcommand instructs the LLM not to invent or paraphrase the
  content.
- `tags`, when non-NULL, is valid JSON for a list of strings. The
  parser tolerates malformed values by returning an empty tuple
  rather than raising.
