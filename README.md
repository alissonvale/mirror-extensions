# Mirror Extensions

A monorepo of stateful extensions for
[Mirror Mind](https://github.com/viniciusteles/mirror).

Mirror Mind is a configuration and memory framework for a Jungian mirror
AI. It ships with two extension *kinds*: **`prompt-skill`** (markdown-only
workflows) and **`command-skill`** (extensions with their own SQLite
tables, CLI subcommands, and Mirror Mode integration). This repository
hosts a collection of `command-skill` extensions that the author uses
day-to-day and is happy to share.

Each subfolder is a self-contained extension. They install one at a
time through the framework's standard CLI:

```bash
git clone https://github.com/alissonvale/mirror-extensions ~/Code/mirror-extensions

python -m memory extensions install <extension-id> \
  --extensions-root ~/Code/mirror-extensions
```

The target mirror home is resolved from `MIRROR_HOME` / `MIRROR_USER`
in the active environment. Pass `--mirror-home <path>` explicitly only
when overriding the default.

## Extensions in this repo

| Folder | Status | What it does |
|---|---|---|
| [`finances/`](finances/) | ✅ Complete (11/11 stories) | Personal and business finance tracking: accounts, transactions, balance snapshots, recurring bills, runway, monthly cash flow, and a `financial_summary` capability that injects live numbers into Mirror Mode for a finance-aware persona. Complete CLI surface: register accounts, record balance snapshots, manage recurring bills and categories, import bank statements (OFX) and credit card statements (CSV), list and filter transactions, compute burn and runway under different assumptions, and migrate from a legacy mirror SQLite database. See [`finances/docs/user-stories/`](finances/docs/user-stories/) for the full story trail. |
| `testimonials/` | ⚪ Planned | A future home for a customer-testimonials extension. Not started. |

## Requirements

- **Mirror Mind** with the stateful extension system
  ([CV14.E1](https://github.com/viniciusteles/mirror/tree/main/docs/product/extensions),
  `command-skill` kind), available on `main` since 2026-05-11.
- **Python 3.10+**.
- **uv** for running the framework's commands.

## Repository layout

```
.
├── LICENSE
├── README.md
├── finances/
│   ├── README.md            -- per-extension entry point
│   ├── skill.yaml
│   ├── SKILL.md
│   ├── extension.py
│   ├── migrations/
│   ├── src/
│   ├── tests/
│   └── docs/
└── testimonials/            -- (placeholder, not started)
```

Every extension follows the layout recommended by the framework's
[Authoring Guide](https://github.com/viniciusteles/mirror/blob/main/docs/product/extensions/authoring-guide.md).

## Running tests

Tests for each extension live under that extension's `tests/`
directory. They depend on Mirror Mind being importable as `memory`,
which today means running them from inside a Mirror Mind checkout's
uv environment:

```bash
# From the Mirror Mind repository root:
uv run pytest ~/Code/mirror-extensions/<extension>/tests/
```

Once Mirror Mind distributes a published package, the tests will run
from the extension's own pyproject without that hop.

## Contributing

These extensions started as a personal port of features from an
earlier mirror prototype to the current framework. Issues and PRs are
welcome, especially:

- new extensions that follow the framework's `command-skill` contract
  and pass a clean review against the
  [Authoring Guide](https://github.com/viniciusteles/mirror/blob/main/docs/product/extensions/authoring-guide.md);
- fixes to the existing extensions;
- documentation improvements.

Open an issue first when in doubt about scope.

## License

[MIT](LICENSE) © Alisson Vale.
