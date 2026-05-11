-- Initial schema for the finances extension.
--
-- Designed to receive the legacy `eco_*` data set used by earlier
-- mirror prototypes without shape changes: the same columns, same
-- types, same constraints.
-- The only thing that moves is the table prefix (eco_ -> ext_finances_)
-- and the table that drops the legacy `eco_recurring_bills` 'category'
-- field overload by keeping it as-is (it carries 'fixed' | 'variable',
-- not a category id).
--
-- Every CREATE/ALTER/DROP must target tables matching ext_finances_*.
-- See docs/product/extensions/migrations.md for the prefix contract.

CREATE TABLE ext_finances_accounts (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    bank            TEXT,
    agency          TEXT,
    account_number  TEXT,
    type            TEXT NOT NULL,                -- 'checking' | 'credit_card' | 'savings'
    entity          TEXT NOT NULL,                -- 'personal' | 'business'
    liquidity       TEXT NOT NULL DEFAULT 'liquid', -- 'liquid' | 'semi_liquid' | 'illiquid'
    opening_balance REAL NOT NULL DEFAULT 0,
    opening_date    TEXT NOT NULL,                -- ISO date
    created_at      TEXT NOT NULL,
    metadata        TEXT
);

CREATE TABLE ext_finances_categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL,                    -- 'income' | 'expense' | 'transfer'
    created_at  TEXT NOT NULL
);

CREATE TABLE ext_finances_transactions (
    id              TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES ext_finances_accounts(id),
    date            TEXT NOT NULL,                -- ISO date
    description     TEXT NOT NULL,
    memo            TEXT,
    amount          REAL NOT NULL,                -- positive = credit, negative = debit
    type            TEXT NOT NULL,                -- 'credit' | 'debit'
    category_id     TEXT REFERENCES ext_finances_categories(id),
    fit_id          TEXT,                         -- bank-side transaction id for dedup
    balance_after   REAL,
    created_at      TEXT NOT NULL,
    metadata        TEXT
);

CREATE TABLE ext_finances_balance_snapshots (
    id          TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL REFERENCES ext_finances_accounts(id),
    date        TEXT NOT NULL,
    balance     REAL NOT NULL,
    source      TEXT NOT NULL DEFAULT 'manual',   -- 'manual' | 'ofx' | 'opening' | 'reconciliation'
    created_at  TEXT NOT NULL
);

CREATE TABLE ext_finances_recurring_bills (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    entity        TEXT NOT NULL,                  -- 'personal' | 'business'
    category      TEXT NOT NULL,                  -- 'fixed' | 'variable'
    amount        REAL NOT NULL,                  -- negative for expenses by convention
    day_of_month  INTEGER,
    notes         TEXT,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE INDEX idx_ext_finances_transactions_account
    ON ext_finances_transactions(account_id);

CREATE INDEX idx_ext_finances_transactions_date
    ON ext_finances_transactions(date);

CREATE INDEX idx_ext_finances_transactions_fit_id
    ON ext_finances_transactions(fit_id);

CREATE INDEX idx_ext_finances_transactions_category
    ON ext_finances_transactions(category_id);

CREATE INDEX idx_ext_finances_balance_snapshots_account
    ON ext_finances_balance_snapshots(account_id);

CREATE INDEX idx_ext_finances_balance_snapshots_date
    ON ext_finances_balance_snapshots(date);
