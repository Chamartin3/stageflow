# StageFlow Python Library Reference

**Version:** 2.0

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core API](#core-api)
3. [Loading Processes](#loading-processes)
4. [Working with Elements](#working-with-elements)
5. [Evaluating Elements](#evaluating-elements)
6. [Understanding Results](#understanding-results)
7. [Schema Generation](#schema-generation)
8. [Process Analysis](#process-analysis)
9. [Registry Operations](#registry-operations)
10. [Error Handling](#error-handling)

---

## Quick Start

```python
from stageflow import load_process, Element

# Load a process definition
process = load_process("workflow.yaml")

# Create an element from your data
element = Element({"email": "user@example.com", "verified": True})

# Evaluate the element
result = process.evaluate(element, "current_stage")

# Check status and get recommended actions
print(result["stage_result"]["status"])   # "incomplete", "blocked", or "ready"
print(result["stage_result"]["actions"])  # List of recommended actions
```

---

## Core API

### Main Imports

```python
from stageflow import (
    # Core functions
    load_process,           # Load process from file or registry
    load_element,           # Load element from file
    create_element,         # Create element from dict

    # Core classes
    Element,                # Element wrapper (alias for DictElement)
    DictElement,            # Dictionary-based element
    Process,                # Process orchestrator
    Stage,                  # Stage validation
    Gate,                   # Gate composition
    Lock,                   # Lock base class

    # Type definitions
    ProcessDefinition,      # Process configuration type
    StageDefinition,        # Stage configuration type
    GateDefinition,         # Gate configuration type
    LockDefinition,         # Lock configuration type
    LockType,               # Lock type enum

    # Result types
    ProcessElementEvaluationResult,
    StageEvaluationResult,
    GateResult,
    LockResult,

    # Action types
    Action,
    ActionType,
)
```

### Loader Imports

```python
from stageflow.loader import (
    ProcessLoader,          # Main loader with error handling
    ProcessLoadResult,      # Unified load result
    LoadError,              # Error details
)
```

### Manager Imports

```python
from stageflow.manager import (
    ProcessManager,         # Multi-process coordinator
    ProcessRegistry,        # File-based process storage
    ManagerConfig,          # Registry configuration
)
```

---

## Loading Processes

### Using `load_process()` (Recommended)

The simplest way to load a process:

```python
from stageflow import load_process

# Load from file
process = load_process("workflow.yaml")
process = load_process("workflow.json")

# Load from registry (use @ prefix)
process = load_process("@my_workflow")

# Raises ProcessLoadError on failure
```

### Using `ProcessLoader` (With Error Details)

For comprehensive error handling:

```python
from stageflow.loader import ProcessLoader

loader = ProcessLoader()
result = loader.load("workflow.yaml")

if result.success and result.process:
    process = result.process
    # Use process
else:
    for error in result.errors:
        print(f"Error: {error.message}")
        print(f"  Location: {error.location}")
        print(f"  Severity: {error.severity}")
```

### Load Result Structure

```python
ProcessLoadResult:
    success: bool               # True if process loaded successfully
    process: Process | None     # The loaded process (if successful)
    errors: list[LoadError]     # List of errors/warnings
    warnings: list[LoadError]   # Non-fatal issues
```

---

## Working with Elements

### Creating Elements

```python
from stageflow import Element, create_element

# From dictionary
element = Element({"email": "user@example.com", "age": 25})

# Using create_element()
element = create_element({"status": "active", "verified": True})

# Nested data
element = Element({
    "user": {
        "profile": {
            "name": "John",
            "email": "john@example.com"
        }
    },
    "orders": [
        {"id": 1, "total": 99.99},
        {"id": 2, "total": 149.99}
    ]
})
```

### Loading Elements from Files

```python
from stageflow import load_element

# Load from JSON or YAML file
element = load_element("user_data.json")
element = load_element("user_data.yaml")
```

### Accessing Properties

```python
element = Element({"user": {"email": "test@example.com"}, "items": [1, 2, 3]})

# Dot notation access
email = element.get_property("user.email")  # "test@example.com"

# Array access
first_item = element.get_property("items[0]")  # 1

# Length function
count = element.get_property("length(items)")  # 3

# Returns None if property doesn't exist
missing = element.get_property("nonexistent")  # None
```

---

## Evaluating Elements

### Basic Evaluation

```python
from stageflow import load_process, Element

process = load_process("workflow.yaml")
element = Element({"email": "user@example.com"})

# Evaluate at specific stage
result = process.evaluate(element, "registration")

# Auto-detect stage (requires stage_prop in process config)
result = process.evaluate(element)
```

### Stage Selection Priority

1. **Explicit parameter** — `process.evaluate(element, "stage_id")`
2. **Auto-detection** — Uses `stage_prop` from process config
3. **Default** — Falls back to `initial_stage`

### Evaluation with Auto-Detection

```yaml
# process.yaml
process:
  name: my_workflow
  stage_prop: "workflow.current_stage"  # Auto-extract stage from element
  initial_stage: draft
  ...
```

```python
element = Element({
    "workflow": {"current_stage": "review"},
    "title": "My Document"
})

# Automatically evaluates at "review" stage
result = process.evaluate(element)
```

---

## Understanding Results

### Result Structure

```python
ProcessElementEvaluationResult = {
    "process_name": str,
    "stage_id": str,
    "stage_result": StageEvaluationResult,
    "regression": bool,
    "regression_details": dict | None,
}

StageEvaluationResult = {
    "status": str,           # "incomplete", "blocked", or "ready"
    "stage_id": str,
    "stage_name": str,
    "missing_properties": list[str],
    "gate_results": dict[str, GateResult],
    "actions": list[Action],
    "ready_gates": list[str],
}
```

### Stage Statuses

| Status | Meaning |
|--------|---------|
| `incomplete` | Element missing required properties defined in `fields` |
| `blocked` | Element has required properties but fails gate validation |
| `ready` | Element passes at least one gate; can transition |

### Working with Results

```python
result = process.evaluate(element, "registration")

# Check status
status = result["stage_result"]["status"]

if status == "incomplete":
    # Show missing properties
    missing = result["stage_result"]["missing_properties"]
    print(f"Missing: {missing}")

elif status == "blocked":
    # Show validation failures
    for gate_name, gate_result in result["stage_result"]["gate_results"].items():
        if not gate_result["passed"]:
            for lock_result in gate_result["lock_results"]:
                if not lock_result["passed"]:
                    print(f"Failed: {lock_result['error_message']}")

elif status == "ready":
    # Show available transitions
    ready_gates = result["stage_result"]["ready_gates"]
    print(f"Can transition via: {ready_gates}")

# Get recommended actions
for action in result["stage_result"]["actions"]:
    print(f"[{action['action_type']}] {action['description']}")
```

### Action Types

| Type | Source | When Generated |
|------|--------|----------------|
| `provide_data` | `computed` | Missing required fields (status: `incomplete`) |
| `resolve_validation` | `computed` | Failed gate locks (status: `blocked`, no configured actions) |
| `execute_action` | `configured` | From stage's `expected_actions` (status: `blocked`) |
| `transition` | `computed` | Ready to move (status: `ready`) |

### Checking Regression

```python
result = process.evaluate(element, "profile_setup")

if result["regression"]:
    details = result["regression_details"]
    print(f"Regressed from: {details['regressed_from']}")
    print(f"Failing stage: {details['failing_stage']}")
```

---

## Schema Generation

Generate JSON Schema for element validation at specific stages.

```python
from stageflow import load_process

process = load_process("workflow.yaml")

# Get cumulative schema (all properties from initial to target stage)
schema = process.get_stage_schema("checkout")

# Get stage-specific schema (only target stage properties)
schema = process.get_stage_schema("checkout", cumulative=False)

# Schema is a JSON Schema (Draft-07) dictionary
import json
print(json.dumps(schema, indent=2))
```

### Schema Modes

**Cumulative (default):**
- Merges schemas from all stages in path from initial to target
- Later stages override earlier stages for duplicate properties
- Required fields include EXISTS locks from all stages

**Stage-Specific:**
- Uses only target stage's `fields` definition
- Required fields include only EXISTS locks from target stage

---

## Process Analysis

### Accessing Process Information

```python
process = load_process("workflow.yaml")

# Process metadata
print(process.name)
print(process.description)
print(process.initial_stage)
print(process.final_stage)

# List all stages
for stage_id, stage in process.stages.items():
    print(f"Stage: {stage_id}")
    print(f"  Name: {stage.name}")
    print(f"  Gates: {list(stage.gates.keys())}")
```

### Consistency Checking

```python
from stageflow.loader import ProcessLoader

loader = ProcessLoader()
result = loader.load("workflow.yaml")

# Check for consistency issues
if result.warnings:
    for warning in result.warnings:
        print(f"Warning: {warning.message}")
        print(f"  Type: {warning.issue_type}")
```

### Issue Types

| Issue | Severity | Description |
|-------|----------|-------------|
| `MISSING_STAGE` | Fatal | Referenced stage doesn't exist |
| `INFINITE_CYCLE` | Fatal | Process has infinite loops |
| `UNREACHABLE_STAGE` | Warning | Stage cannot be reached from initial |
| `FINAL_STAGE_HAS_GATES` | Warning | Final stage has outgoing transitions |
| `DUPLICATE_GATE_SCHEMAS` | Warning | Multiple gates with identical validation |

---

## Registry Operations

### Using ProcessManager

```python
from stageflow.manager import ProcessManager, ManagerConfig

# Configure registry
config = ManagerConfig(processes_dir="./processes")
manager = ProcessManager(config)

# List all processes
processes = manager.list_processes()
for name, info in processes.items():
    print(f"@{name}: {info['description']}")

# Load from registry
process = manager.load("@my_workflow")

# Import a process
manager.import_process("workflow.yaml", name="my_workflow")

# Export a process
manager.export_process("my_workflow", "exported.yaml")

# Delete a process
manager.delete_process("old_workflow")
```

### Using ProcessRegistry Directly

```python
from stageflow.manager import ProcessRegistry

registry = ProcessRegistry("./processes")

# Check if process exists
if registry.exists("my_workflow"):
    process = registry.load("my_workflow")

# Get process path
path = registry.get_path("my_workflow")
```

---

## Error Handling

### Load Errors

```python
from stageflow.loader import ProcessLoader, LoadError

loader = ProcessLoader()
result = loader.load("workflow.yaml")

if not result.success:
    for error in result.errors:
        print(f"Error: {error.message}")
        print(f"  Location: {error.location}")
        print(f"  Severity: {error.severity}")
        print(f"  Type: {error.error_type}")
```

### Error Types

| Category | Examples |
|----------|----------|
| **File Errors** | Not found, permission denied, encoding issues |
| **Parse Errors** | Invalid YAML/JSON syntax |
| **Structure Errors** | Missing required fields, invalid types |
| **Configuration Errors** | Invalid locks, gates, stages |
| **Consistency Errors** | Cycles, unreachable stages |

### Exception Handling

```python
from stageflow import load_process
from stageflow.loader import ProcessLoadError

try:
    process = load_process("workflow.yaml")
except ProcessLoadError as e:
    print(f"Failed to load: {e}")
except FileNotFoundError:
    print("Process file not found")
```

---

## Complete Example

```python
from stageflow import load_process, Element

# Load process
process = load_process("user_onboarding.yaml")

# Simulate user data at different stages
def check_user_status(user_data: dict, stage: str = None):
    element = Element(user_data)
    result = process.evaluate(element, stage)

    status = result["stage_result"]["status"]
    stage_name = result["stage_result"]["stage_name"]

    print(f"\n=== {stage_name} ===")
    print(f"Status: {status}")

    if status == "incomplete":
        print(f"Missing: {result['stage_result']['missing_properties']}")

    elif status == "blocked":
        print("Actions needed:")
        for action in result["stage_result"]["actions"]:
            print(f"  - {action['description']}")

    elif status == "ready":
        gates = result["stage_result"]["ready_gates"]
        print(f"Ready to transition via: {gates}")

    if result["regression"]:
        print(f"WARNING: Regression detected!")

    return result

# Test progression
check_user_status({"email": "user@test.com"}, "registration")
check_user_status({"email": "user@test.com", "verified": True}, "registration")
check_user_status({"email": "user@test.com", "verified": True, "name": "John"}, "profile_setup")
```

---

## See Also

- [CLI Reference](./CLI_REFERENCE.md) — Command-line interface documentation
- [Process Schema Reference](./PROCESS_SCHEMA_REFERENCE.md) — YAML/JSON schema format
- [Lock Types Reference](./LOCK_TYPES_REFERENCE.md) — All 14 lock types
- [Action Design Best Practices](./ACTION_DESIGN_BEST_PRACTICES.md) — Writing effective actions
