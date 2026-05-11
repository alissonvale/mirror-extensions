# Maestro Architecture

Maestro is a Mirror-native coherence engine for project journeys. The extension
itself is installed into Mirror, but the coherence state it manages remains in
the target project.

## Three folders, three roles

| Role | Current example | Purpose |
|---|---|---|
| Extension source | `~/Code/mirror-extensions/maestro` | Where the Maestro extension is developed. Commit source changes here. |
| Installed runtime | `~/.mirror/<user>/extensions/maestro` | Copy loaded by Pi/Mirror at runtime after `extensions install`. Do not edit directly. |
| Journey target project | `~/Code/sandbox-pet-food` | A project observed or bootstrapped by Maestro through its journey `project_path`. |

The installed runtime is the executable copy. The source tree is the versioned
copy. The target project is the work being kept coherent.

## Current journeys

```text
journey/maestro
  -> ~/Code/mirror-extensions/maestro
  -> source-code development of this extension

journey/sandbox-pet-food
  -> ~/Code/sandbox-pet-food
  -> example online pet food store, built using Maestro

~/.mirror/<user>/extensions/maestro
  -> installed runtime loaded by Pi/Mirror
```

## Source of truth

Maestro's first slice keeps canonical coherence state in the project, not in
Mirror's database:

```text
<project>/maestro.yml
<project>/docs/coherence/rules.md
<project>/docs/coherence/index.md
```

The database stores operational history and bindings:

```text
ext_maestro_check_runs       # check summaries
_ext_bindings                # core table: capability -> persona/journey/global
identity.metadata.project_path # core identity metadata: journey -> project root
```

## Base lens

The hello-world lens has two Units of Coherence (UoCs):

| ID | Semantic ID | Severity | Meaning |
|---|---|---|---|
| UoC-001 | `project.working_name` | blocking | Every Maestro project has a provisional working name. |
| UoC-002 | `project.git_repository` | important | Every Maestro project should be tracked in git. |

`project.git_repository` is monorepo-aware: a project is considered versioned
when `.git` exists either at the project root or in one of its parent
directories.

## Runtime flow

When Mirror Mode loads a journey bound to `maestro/coherence_status`:

```text
active journey
   ↓
identity.metadata.project_path
   ↓
project root
   ↓
installed extension runtime: ~/.mirror/<user>/extensions/maestro
   ↓
coherence_status provider
   ↓
live check of the project root
   ↓
context block injected into Mirror Mode
```

The provider never raises into Mirror Mode. If the journey has no project path
or the check fails, it logs and returns `None`.

## Development cycle

Edit source:

```bash
cd ~/Code/mirror-extensions/maestro
```

Run tests from the Mirror checkout:

```bash
cd ~/Code/mirror
uv run ruff format ~/Code/mirror-extensions/maestro
uv run ruff check ~/Code/mirror-extensions/maestro
uv run pytest ~/Code/mirror-extensions/maestro/tests -q
```

Install the updated runtime:

```bash
uv run python -m memory extensions install maestro \
  --extensions-root ~/Code/mirror-extensions
```

Then Mirror Mode will use the updated copy from:

```text
~/.mirror/<user>/extensions/maestro
```
