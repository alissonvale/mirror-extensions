# Maestro Bindings

Maestro uses journey bindings so its coherence status appears automatically in
Mirror Mode when a project journey is active.

## Two links are required

### 1. Point a journey at a project

```bash
uv run python -m memory journey set-path <journey_id> /path/to/project
```

This answers:

> Which folder represents this journey?

It stores `project_path` in the journey identity metadata.

### 2. Bind Maestro to the journey

```bash
uv run python -m memory ext maestro bind coherence_status --journey <journey_id>
```

This answers:

> Which Maestro capability should run automatically when this journey is active
> in Mirror Mode?

It writes a row to the core `_ext_bindings` table.

The two links are independent. `set-path` locates the project; `bind` activates
automatic context injection.

## Current bindings

```text
maestro/coherence_status -> journey/maestro
maestro/coherence_status -> journey/sandbox-pet-food
```

Current project paths:

```text
journey/maestro           -> ~/Code/mirror-extensions/maestro
journey/sandbox-pet-food  -> ~/Code/sandbox-pet-food
```

## Setup commands

### Maestro extension development journey

```bash
uv run python -m memory journey set-path maestro ~/Code/mirror-extensions/maestro
uv run python -m memory ext maestro bind coherence_status --journey maestro
```

### Sandbox Pet Food example app

```bash
uv run python -m memory journey set-path sandbox-pet-food ~/Code/sandbox-pet-food
uv run python -m memory ext maestro bind coherence_status --journey sandbox-pet-food
```

## Verify bindings

```bash
uv run python -m memory ext maestro bindings
```

Expected shape:

```text
=== bindings for extension/maestro ===
  coherence_status -> journey/maestro
  coherence_status -> journey/sandbox-pet-food
```

Verify project paths:

```bash
uv run python - <<'PY'
from memory.client import MemoryClient
mem = MemoryClient()
for journey in ["maestro", "sandbox-pet-food"]:
    print(journey, "->", mem.journeys.get_project_path(journey))
PY
```

## What happens in Mirror Mode

If the user says:

```text
let's work on Sandbox Pet Food
```

Mirror detects `journey=sandbox-pet-food`. Because the capability is bound to
that journey, Mirror loads the installed Maestro extension and calls
`coherence_status`. The provider then reads the journey project path and checks:

```text
~/Code/sandbox-pet-food/maestro.yml
~/Code/sandbox-pet-food/docs/coherence/rules.md
~/Code/sandbox-pet-food/docs/coherence/index.md
.git at or above ~/Code/sandbox-pet-food
```

The returned block is injected under:

```text
=== extension/maestro/coherence_status ===
```

## Unbind

```bash
uv run python -m memory ext maestro unbind coherence_status --journey sandbox-pet-food
```

Use this when a journey should no longer receive automatic Maestro context.
Direct CLI commands still work without a binding.
