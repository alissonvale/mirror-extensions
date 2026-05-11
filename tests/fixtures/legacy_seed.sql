-- Synthetic legacy mirror finance dataset for tests.
--
-- A tiny but representative shape:
--   2 personal-entity accounts (one checking, one credit card)
--   1 business-entity account
--   1 expense category
--   2 balance snapshots
--   4 transactions (one of each: credit, debit, with category, without)
--   1 active recurring bill
--   1 inactive recurring bill
--
-- The structure mirrors the legacy schema verbatim.

CREATE TABLE eco_accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    bank TEXT,
    agency TEXT,
    account_number TEXT,
    type TEXT NOT NULL,
    entity TEXT NOT NULL,
    opening_balance REAL NOT NULL DEFAULT 0,
    opening_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT,
    liquidity TEXT NOT NULL DEFAULT 'liquid'
);

CREATE TABLE eco_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE eco_transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES eco_accounts(id),
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    memo TEXT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category_id TEXT REFERENCES eco_categories(id),
    fit_id TEXT,
    balance_after REAL,
    created_at TEXT NOT NULL,
    metadata TEXT
);

CREATE TABLE eco_balance_snapshots (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES eco_accounts(id),
    date TEXT NOT NULL,
    balance REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL
);

CREATE TABLE eco_recurring_bills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    day_of_month INTEGER,
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Accounts.
INSERT INTO eco_accounts VALUES
  ('acc00001', 'Test Checking', 'TestBank', '0001', '12345', 'checking',
   'personal', 0.0, '2026-01-01', '2026-01-01T00:00:00Z', NULL, 'liquid'),
  ('acc00002', 'Test Credit Card', 'TestBank', NULL, '9999', 'credit_card',
   'personal', 0.0, '2026-01-01', '2026-01-01T00:00:00Z', NULL, 'liquid'),
  ('acc00003', 'Test Business', 'TestBank', '0002', '54321', 'checking',
   'business', 10000.0, '2026-01-01', '2026-01-01T00:00:00Z', NULL, 'liquid');

-- Category.
INSERT INTO eco_categories VALUES
  ('cat00001', 'groceries', 'expense', '2026-01-01T00:00:00Z');

-- Snapshots.
INSERT INTO eco_balance_snapshots VALUES
  ('snp00001', 'acc00001', '2026-02-01', 1234.56, 'manual', '2026-02-01T00:00:00Z'),
  ('snp00002', 'acc00003', '2026-02-01', 8500.00, 'ofx',    '2026-02-01T00:00:00Z');

-- Transactions.
INSERT INTO eco_transactions VALUES
  ('txn00001', 'acc00001', '2026-01-15', 'Salary',          NULL,  3000.00, 'credit', NULL,        'fit-1', NULL, '2026-01-15T00:00:00Z', NULL),
  ('txn00002', 'acc00001', '2026-01-16', 'Supermarket',     NULL,  -123.45, 'debit',  'cat00001',  'fit-2', NULL, '2026-01-16T00:00:00Z', NULL),
  ('txn00003', 'acc00002', '2026-01-20', 'Online Purchase', NULL,  -50.00,  'debit',  NULL,        'fit-3', NULL, '2026-01-20T00:00:00Z', NULL),
  ('txn00004', 'acc00003', '2026-01-25', 'Client Payment',  'PIX', 5000.00, 'credit', NULL,        NULL,    NULL, '2026-01-25T00:00:00Z', NULL);

-- Recurring bills.
INSERT INTO eco_recurring_bills VALUES
  ('bil00001', 'Rent',       'personal', 'fixed',    -1500.0, 5,   'monthly rent',  1, '2026-01-01T00:00:00Z'),
  ('bil00002', 'Old gym',    'personal', 'variable', -100.0,  10,  'cancelled',     0, '2026-01-01T00:00:00Z');
