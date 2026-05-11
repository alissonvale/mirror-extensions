[< finances](../README.md)

# Bindings

The finances extension exposes one Mirror Mode context capability.

## `financial_summary`

**What it returns.** A compact markdown block summarising the user's
current financial state: liquid and semi-liquid totals, monthly cash
flow per month (income / expense / net), monthly burn from active
recurring bills, and runway derived from the latest balance snapshots.

The output is bounded in length (one section header per category, one
row per month over the last six months). It returns `None` when the
database is empty so no section is injected into the prompt.

**When it fires.** Every Mirror Mode turn whose active persona is
bound to this capability. The provider does not branch on the user's
query — once bound, it always fires when the persona is active.

**Suggested personas.** `tesoureira` (Portuguese baseline name in
this user's identity), or any persona that talks about money:
`treasurer`, `cfo`, `founder`. The suggestion is informational; the
user picks.

**Dependencies on data.** The provider reads
`ext_finances_accounts`, `ext_finances_balance_snapshots`,
`ext_finances_transactions`, and `ext_finances_recurring_bills`. If
all four are empty the provider returns `None`. If only some are
empty, the corresponding section is omitted.

**Performance.** Pure SQL aggregation; no LLM or network call.

## Binding the capability

```bash
python -m memory ext finances bind financial_summary --persona tesoureira
python -m memory ext finances bindings
```

To remove the binding:

```bash
python -m memory ext finances unbind financial_summary --persona tesoureira
```

Multiple personas can be bound to the same capability; the provider
runs once per active persona.

## What a Mirror Mode turn looks like

When the bound persona is active, the assembled prompt contains a new
section near the end:

```
=== extension/finances/financial_summary ===
--- Liquid (immediately available) ---
[PF] Itaú CC alisson — R$ 12,345.67 (on 2026-05-09)
[PF] Nubank RDB — R$ 94,123.10 (on 2026-05-10)
Subtotal: R$ 106,468.77

--- Cash flow ---
2026-03: in R$ 5,000.00 | out R$ 9,876.54 | net R$ -4,876.54
2026-04: in R$ 0.00     | out R$ 10,475.12 | net R$ -10,475.12

--- Burn & runway ---
Monthly burn (from bills): R$ 10,475.12
Runway (liquid only): 10.2 months
```

The persona reads this block as fresh, deterministic context and
phrases the answer in her own voice.
