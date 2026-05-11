---
name: "ext-finances"
description: Personal and business finance tracking — accounts, transactions, snapshots, recurring bills, burn rate and runway.
user-invocable: true
---

# Finances

Tracks personal and business cash flow. Owns accounts (checking, credit
card, savings), individual transactions, periodic balance snapshots, and
recurring bills. Computes monthly burn rate and runway from either
recorded bills or transaction history.

## Commands

- `python -m memory ext finances accounts` — list all accounts.
- `python -m memory ext finances accounts add <args>` — register a new account.
- `python -m memory ext finances snapshot <account> <date> <balance>` — record a balance snapshot.
- `python -m memory ext finances balance [account]` — show current balance(s).
- `python -m memory ext finances transactions [--account <id>] [--from <date>] [--to <date>]` — list transactions.
- `python -m memory ext finances import-statement <file> [--format ofx] [--account <id>]` — import a bank statement (OFX or compatible).
- `python -m memory ext finances import-credit-card-statement <file> [--format csv-itau-cc] [--account <id>]` — import a credit card statement.
- `python -m memory ext finances bills [add | list | remove <id>]` — manage recurring bills.
- `python -m memory ext finances runway [--include-liquidity liquid,semi_liquid] [--burn-source bills|history]` — compute runway.
- `python -m memory ext finances report [--account <id>]` — monthly income/expense/net.
- `python -m memory ext finances categorize <transaction-id> <category>` — categorize a transaction.
- `python -m memory ext finances migrate-legacy --source <path>` — import all data from a legacy mirror SQLite database that carries the `eco_*` schema.

## When the agent should use this

User queries about money — balances, runway, burn, spending categories,
imports of bank statements or credit card statements, recurring bills,
runway projections — should route to this extension. A finance-aware
persona (e.g. `treasurer`) can have the `financial_summary` capability
bound, in which case a live summary is injected into Mirror Mode
automatically when that persona is active; the agent does not need to
call commands explicitly to ground its answer in current numbers.

For specific lookups (a single transaction, a category breakdown, a
runway calculation under different assumptions), call the relevant
subcommand directly.

## What the agent should not do

- Do not invent balances or transactions. The data layer is the source
  of truth; if a number is not in the database, say so or run an
  import.
- Do not summarize transactions by re-running an LLM over their
  descriptions — use the `report` command, which is deterministic.
- Do not store sensitive numbers in conversation memory; the data
  already lives in the extension's tables.
