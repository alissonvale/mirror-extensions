# Maestro Commands

Run Maestro commands from the Mirror checkout so the framework environment is
loaded through `uv`:

```bash
cd ~/Code/mirror
```

## Install or reinstall

After editing the source in `~/Code/mirror-extensions/maestro`, install the
runtime copy:

```bash
uv run python -m memory extensions install maestro \
  --extensions-root ~/Code/mirror-extensions
```

Pi/Mirror loads the installed copy from:

```text
~/.mirror/<user>/extensions/maestro
```

## Check a journey project

```bash
uv run python -m memory ext maestro check --journey maestro
uv run python -m memory ext maestro check --journey sandbox-pet-store
```

`check` resolves the journey's `project_path`, evaluates the base lens, updates
`docs/coherence/index.md`, and writes a summary row to
`ext_maestro_check_runs`.

## Configure locale and mode

```bash
uv run python -m memory ext maestro configure \
  --journey sandbox-pet-store \
  --locale pt-BR \
  --mode technical
```

Supported values:

```text
locale: en-US | pt-BR
mode: technical | non-technical
```

This writes `maestro.yml` and `docs/coherence/rules.md`. It does not require a
project name.

## Initialize a project name

```bash
uv run python -m memory ext maestro init \
  --journey sandbox-pet-store \
  --name "Sandbox"
```

This resolves `UoC-001/project.working_name` by writing:

```text
maestro.yml
README.md
docs/coherence/rules.md
docs/coherence/index.md
```

## Operate without a journey

Every command also accepts `--root` for one-off use:

```bash
uv run python -m memory ext maestro check --root ~/Code/sandbox-pet-store
uv run python -m memory ext maestro init --root ~/Code/new-project --name "New Project"
```

With `--root`, Maestro does not need a configured journey path and does not
record a journey id in check history.

## View check history

```bash
sqlite3 ~/.mirror/<user>/memory.db \
  "SELECT created_at, journey_id, project_root, open_count, blocking_count, important_count, summary
   FROM ext_maestro_check_runs
   ORDER BY created_at DESC
   LIMIT 10;"
```

## Typical flow for a new project journey

```bash
# 1. Create project folder
mkdir -p ~/Code/sandbox-pet-store

# 2. Ensure the journey points to it
uv run python -m memory journey set-path sandbox-pet-store ~/Code/sandbox-pet-store

# 3. Bind automatic Mirror Mode context
uv run python -m memory ext maestro bind coherence_status --journey sandbox-pet-store

# 4. Configure human surface
uv run python -m memory ext maestro configure \
  --journey sandbox-pet-store \
  --locale pt-BR \
  --mode technical

# 5. Resolve the project-name UoC
uv run python -m memory ext maestro init \
  --journey sandbox-pet-store \
  --name "Sandbox"

# 6. Check current coherence
uv run python -m memory ext maestro check --journey sandbox-pet-store
```

The current expected result for Sandbox Pet Store is:

```text
✓ UoC-001 Project working name: resolved
• UoC-002 Git repository: open
⚠️  Attention - non-blocking coherence gaps found.
```

Resolve `UoC-002` with:

```bash
cd ~/Code/sandbox-pet-store
git init
cd ~/Code/mirror
uv run python -m memory ext maestro check --journey sandbox-pet-store
```
