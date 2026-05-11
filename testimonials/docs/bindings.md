[< testimonials](../README.md)

# Mirror Mode bindings

The extension ships one Mirror Mode capability: `recent_testimonials`
(US-05). Bind it to any persona that benefits from having the
customer's voice nearby during reflection.

## How the capability works

When a Mirror Mode turn is dispatched to a persona that has
`recent_testimonials` bound, the framework calls
`provide_recent_testimonials(api, ctx)` from `src/context.py`. The
provider:

1. Reads `ctx.query` (the user's message for this turn).
2. Embeds the query and runs cosine search over every stored
   testimonial's embedding.
3. Keeps hits with score ≥ `RELEVANCE_FLOOR` (default 0.30),
   capped at `MAX_HITS` (default 3).
4. Returns a compact markdown block, or `None` when nothing
   clears the floor.

`None` is the common case for off-topic conversations. The framework
does not inject anything when the provider returns `None`, so the
prompt stays clean.

## Recommended bindings

There is no single right answer; bind wherever the customer voice
adds depth to the reflection.

| Persona kind | Why bind |
|---|---|
| writer / `escritora` | Drafting copy, articles, emails — paraphrased customer language often unlocks the right opening line. |
| marketer / `divulgadora` | Launches, announcements, social-proof choices. |
| editor / `editor` | Reviewing copy a peer wrote; surfaces existing testimonials that could replace a generic claim with a real quote. |

For projects whose entire purpose is a launch or campaign, binding
**to the journey** instead of (or in addition to) a persona can make
sense — testimonials related to that product will then surface across
every persona while the journey is active.

## Bind

```bash
python -m memory ext testimonials bind recent_testimonials \
  --persona <persona-id>
```

To bind to a journey:

```bash
python -m memory ext testimonials bind recent_testimonials \
  --journey <journey-slug>
```

## Unbind

```bash
python -m memory ext testimonials unbind recent_testimonials \
  --persona <persona-id>
```

## Tuning

Two module-level constants in `src/context.py` are the dials worth
knowing about:

- `RELEVANCE_FLOOR` (default `0.30`) — increase to inject only very
  strong matches; decrease to be more liberal.
- `MAX_HITS` (default `3`) — increase to inject more testimonials
  per turn; decrease for tighter prompts.

Both are safe to edit in a personal fork; no migration is required.

## Cost note

Each Mirror Mode turn under a bound persona pays for one embedding
call (≈ $0.00002 on `text-embedding-3-small`) plus a cosine search
over every stored testimonial. With a few hundred rows this is
trivial; with thousands you may want to revisit the search path.
