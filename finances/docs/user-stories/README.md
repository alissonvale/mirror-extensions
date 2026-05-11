[< finances](../../README.md)

# User stories

The user stories that drive the construction of the finances extension.
Each story is a small, end-to-end slice of value.

## Order

The implementation order prioritises bringing the legacy data in
first. With real data present, every other story is exercised against
production-shape numbers from its first test run.

| # | Story | Status |
|---|-------|--------|
| US-11 | [Migrate legacy data](US-11-migrate-legacy-data.md) | ✅ Done |
| US-01 | [Register and list accounts](US-01-register-and-list-accounts.md) | ⚪ Planned |
| US-02 | [Record balance snapshot](US-02-record-balance-snapshot.md) | ⚪ Planned |
| US-05 | [List and filter transactions](US-05-list-and-filter-transactions.md) | ⚪ Planned |
| US-08 | [Monthly cash flow report](US-08-monthly-cash-flow-report.md) | ⚪ Planned |
| US-06 | [Manage recurring bills](US-06-manage-recurring-bills.md) | ⚪ Planned |
| US-07 | [Calculate burn and runway](US-07-calculate-burn-and-runway.md) | ⚪ Planned |
| US-10 | [Inject financial context into Mirror Mode](US-10-inject-financial-context-into-mirror-mode.md) | ✅ Done |
| US-03 | [Import bank statement](US-03-import-bank-statement.md) | ⚪ Planned |
| US-04 | [Import credit card statement](US-04-import-credit-card-statement.md) | ⚪ Planned |
| US-09 | [Categorize transactions](US-09-categorize-transactions.md) | ⚪ Planned |

This order is a suggestion. The schema is shared across all stories,
so any of US-01..US-10 can move forward after US-11 closes; the table
above is the order I expect to actually implement them in.

## Story file structure

Each file follows the three-section convention recommended in the
framework's
[Authoring Guide](../../../../mirror/docs/product/extensions/authoring-guide.md):

1. **Story** — narrative (As a / I want / so that), motivation,
   acceptance value.
2. **Plan** — files to add or change, sequence, decisions inherited
   from earlier stories.
3. **Test Guide** — cases by component, edge cases, done criteria.

Stories with status ⚪ Planned currently have lighter Plan and Test
Guide sections. Those sections are fleshed out at the time of
implementation, alongside the code that closes the story.
