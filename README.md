# StageFlow

A declarative, data-centric state machine.  Manages workflow defining and validating multi-stage processes.

Define workflows as YAML/JSON schemas, evaluate where data stands within them, and get actionable feedback for progression.

## Installation

### Quick Setup

Add the `bin` folder to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="/path/to/stageflow/bin:$PATH"
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

Now you can run `stageflow` from anywhere:

```bash
stageflow --help
```

### Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

Dependencies are managed automatically via `uv` when running the CLI.

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Process** | Workflow definition with stages, transitions, and validation rules |
| **Stage** | Checkpoint defining expected data shape and transition gates |
| **Element** | Your data as JSON (documents, users, orders, etc.) |
| **Gate** | Transition rule combining locks to validate progression |
| **Lock** | Validation predicate (EXISTS, EQUALS, REGEX, RANGE, etc.) |


## Usage

StageFlow provides two interfaces: a **Python library** for integration into applications, and a **CLI** for workflow management and scripting.

### Python Library

Use the library to embed workflow evaluation directly in your application.

```python
from stageflow import load_process, Element

# Load process from file or registry
process = load_process("onboarding.yaml")  # or "@registered_name"

# Create element from your data
element = Element({"email": "user@example.com", "verified": True})

# Evaluate element against current stage
result = process.evaluate(element, "email_verification")

# Check results
print(result["stage_result"]["status"])  # "incomplete", "blocked", or "ready"
print(result["stage_result"]["actions"])  # Recommended next actions
print(result["regression"])               # Backward movement detected?
```

**Library Workflows:**

| Workflow | Description |
|----------|-------------|
| **Evaluate Elements** | Determine stage status and available transitions |
| **Schema Generation** | Get JSON Schema for stage validation |
| **Process Analysis** | Detect consistency issues (cycles, unreachable stages) |
| **Registry Access** | Load processes by name with `@name` syntax |

See [docs/lib/LIBRARY_REFERENCE.md](docs/lib/LIBRARY_REFERENCE.md) for complete API documentation.

---

### Command Line Interface

Use the CLI for process management, visualization, and scripting.

```bash
# Evaluate an element against a process
stageflow evaluate process.yaml -e element.json

# View process details and validation status
stageflow process view process.yaml

# Generate Mermaid flowchart
stageflow process diagram process.yaml -o diagram.md

# Generate JSON Schema for a stage
stageflow process schema process.yaml checkout -o schema.json

# Create new process from template
stageflow process new my_workflow.yaml

# Registry management
stageflow process registry list
stageflow process registry import process.yaml --name my_process
```

**CLI Workflows:**

| Workflow | Command |
|----------|---------|
| **Evaluate Elements** | `stageflow evaluate <process> -e <element>` |
| **Inspect Process** | `stageflow process view <process>` |
| **Visualize** | `stageflow process diagram <process>` |
| **Generate Schema** | `stageflow process schema <process> <stage>` |
| **Create Process** | `stageflow process new <name>` |
| **Manage Registry** | `stageflow process registry <list\|import\|export\|delete>` |

See [CLI_REFERENCE.md](CLI_REFERENCE.md) for complete command documentation.

---

## Core Features

- **14 Lock Types**: EXISTS, EQUALS, REGEX, RANGE, CONDITIONAL, OR_LOGIC, and more
- **3 Stage Statuses**: `incomplete` → `blocked` → `ready`
- **Regression Detection**: Track backward movement with configurable policy
- **Consistency Analysis**: Detect cycles, unreachable stages, orphans
- **Schema Generation**: Auto-generate JSON Schema per stage
- **Process Registry**: Store and reuse processes with `@name` syntax
- **Visualization**: Mermaid flowcharts and documentation generation

---

## Evaluation Pipeline

1. **Load & Validate** — Parse process config, run consistency checks
2. **Stage Evaluation** — Check element properties against stage requirements
3. **Gate Analysis** — Evaluate locks to determine available transitions
4. **Regression Detection** — Validate against previous stages (if enabled)
5. **Result Generation** — Return status, actions, and recommendations

---

## Process Definition Example

```yaml
process:
  name: user_onboarding
  initial_stage: registration
  final_stage: active

  stages:
    registration:
      fields: [email, password]
      gates:
        verify_email:
          target_stage: profile_setup
          locks:
            - exists: email
            - type: regex
              property_path: email
              expected_value: "^[^@]+@[^@]+$"

    profile_setup:
      fields: [name, bio]
      gates:
        complete_profile:
          target_stage: active
          locks:
            - exists: name
            - type: not_empty
              property_path: name

    active:
      fields: [email, name]
```

---

## Development

```bash
uv run pytest                    # Run tests
uv run ruff check --fix .        # Lint
uv run pyright                   # Type check
```

## License

MIT
