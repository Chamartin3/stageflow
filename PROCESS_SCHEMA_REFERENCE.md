# StageFlow Process Schema Reference

---

## Table of Contents

1. [File Structure](#file-structure)
2. [Process Object](#process-object)
3. [Stage Object](#stage-object)
4. [Fields Definition](#fields-definition)
5. [Expected Actions](#expected-actions)
6. [Gate Object](#gate-object)
7. [Lock Object](#lock-object)
8. [Property Path Notation](#property-path-notation)

---

## File Structure

All StageFlow process definitions are wrapped in a `process:` root key.

```yaml
process:
  name: <string>
  initial_stage: <string>
  final_stage: <string>
  stages:
    <stage_id>: <Stage>
```

---

## Process Object

The **Process** is the root object that defines the complete workflow.

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | ✓ | Unique identifier for the process |
| `description` | string | ✓ | Human-readable workflow description |
| `initial_stage` | string | ✓ | Stage where elements begin |
| `final_stage` | string | ✓ | Stage representing completion |
| `stage_prop` | string | | Property path for automatic stage detection |
| `regression_policy` | string | | How to handle regression: `"ignore"`, `"warn"` (default), or `"block"` |
| `stages` | object | ✓ | Dictionary of stage definitions (key = stage ID) |

### Specification

```yaml
process:
  name: <string>                    # Required: Process identifier
  description: <string>             # Required: Process description
  initial_stage: <string>           # Required: Must exist in stages
  final_stage: <string>             # Required: Must exist in stages
  stage_prop: <string>              # Optional: Property path (e.g., "workflow.stage")
  regression_policy: <string>       # Optional: "ignore", "warn", or "block"
  stages:                           # Required: Map of stage_id -> Stage object
    <stage_id>: <Stage>
```

### Automatic Stage Detection

When `stage_prop` is configured, StageFlow automatically extracts the current stage from element data.

**Stage Selection Precedence:**
1. Explicit override (API parameter or CLI flag)
2. Auto-extraction from `stage_prop` property path
3. Default to `initial_stage`

---

## Stage Object

A **Stage** represents a checkpoint in the workflow where elements must meet specific criteria.

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | | Display name for the stage |
| `description` | string | | Human-readable explanation of this stage |
| `fields` | list/object | ✓ | Properties expected at this stage |
| `expected_actions` | array | | User-defined recommended actions |
| `gates` | object | ✓ | Dictionary of gate definitions (key = gate name) |
| `is_final` | boolean | | Marks stage as terminal (no gates required) |

### Specification

```yaml
<stage_id>:
  name: <string>                           # Optional: Display name
  description: <string>                    # Optional: Stage description
  fields:                                  # Required: Expected properties
    - <property_path>
  expected_actions:                        # Optional: Array of Action objects
    - <Action>
  gates:                                   # Required: Map of gate_name -> Gate object
    <gate_name>: <Gate>
  is_final: <boolean>                      # Optional: Default false
```

### Example

```yaml
email_verification:
  name: "Email Verification"
  description: "User must verify email address via confirmation link; expires after 24 hours."
  fields:
    - email
    - meta.signup_date
  expected_actions:
    - name: "send_verification"
      description: "Send verification email to user"
      related_properties:
        - "email"
  gates:
    email_verified:
      target_stage: "profile_setup"
      locks:
        - type: exists
          property_path: "meta.email_verified_at"
          error_message: "Email must be verified before proceeding"
```

---

## Fields Definition

The `fields` property defines which properties are expected at a stage. StageFlow supports three syntax levels.

### Level 1: Simple List

```yaml
fields:
  - email
  - password
  - user.profile.name
```

### Level 2: Type Shortcuts

```yaml
fields:
  email: string
  age: int
  is_active: bool
```

### Level 3: Full Property Specs (Recommended)

```yaml
fields:
  email:
    type: string
    default: null
  age:
    type: int
    default: 0
  profile:
    type: dict
```

**Supported Types:** `str`, `string`, `int`, `integer`, `float`, `bool`, `boolean`, `list`, `dict`, `dictionary`

---

## Expected Actions

**Expected Actions** provide user-defined guidance for progressing through a stage.

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | ✓ | Unique identifier for the action (snake_case) |
| `description` | string | ✓ | Brief summary of what user needs to do (one sentence, imperative) |
| `instructions` | array | ✓ | Step-by-step guidelines (empty array if none, final step describes result format) |
| `related_properties` | array | | Properties used as **input** to execute the action (context/dependencies) |
| `target_properties` | array | | Properties that **capture the result** of the action (output/where results are stored) |

### Related vs Target Properties

- **`related_properties`**: Properties that provide context or are needed to **execute** the action. These are inputs or dependencies.
- **`target_properties`**: Properties that will be **set or modified** as a result of completing the action. These capture the output. Each target property should have clearly defined format and characteristics (type, constraints, content requirements).

**Important:** The final instruction should describe the expected result format for the target properties (e.g., "Resolution should be 2-5 paragraphs", "Photo must be JPG/PNG, 500KB-5MB").

**Example:**
```yaml
expected_actions:
  - name: "verify_email"
    description: "Verify your email address"
    instructions:
      - "Check your inbox for verification email"
      - "Click the verification link in the email"
      - "Return to this page after verification"
      - "Verification sets 'verified' to true and 'verified_at' to ISO 8601 timestamp"
    related_properties:
      - "email"           # Input: needed to send verification email
    target_properties:
      - "verified"        # Output: boolean true after verification
      - "verified_at"     # Output: string ISO 8601 timestamp
```

### Specification

```yaml
expected_actions:
  - name: <string>                     # Required: Unique identifier (snake_case)
    description: <string>              # Required: Brief action summary (one sentence)
    instructions:                      # Required: Step-by-step guide (empty array if none)
      - <string>
    related_properties:                # Optional: Input properties (array, defaults to [])
      - <string>
    target_properties:                 # Optional: Output properties (array, defaults to [])
      - <string>
```

**Field Requirements:**

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `name` | ✓ | - | Unique identifier in snake_case |
| `description` | ✓ | - | One sentence, imperative mood |
| `instructions` | ✓ | `[]` | Always present, empty array if no steps |
| `related_properties` | | `[]` | Input/context properties |
| `target_properties` | | `[]` | Output/result properties |

**Note:** See [ACTION_DESIGN_BEST_PRACTICES.md](ACTION_DESIGN_BEST_PRACTICES.md) for comprehensive guidance on writing effective actions.

---

## Action Types (Evaluation Results)

When you evaluate an element, StageFlow returns **actions** in the evaluation result. Each action has a `action_type` and `source` indicating its origin and purpose.

### ActionType Enum

| Value | Description | When Generated |
|-------|-------------|----------------|
| `provide_data` | User needs to provide missing data | Stage status is `incomplete` (missing required fields) |
| `resolve_validation` | Auto-generated from failed gate locks | Stage status is `blocked` and no configured actions exist |
| `execute_action` | Configured action from `expected_actions` | Stage status is `blocked` and stage has `expected_actions` |
| `transition` | Ready to move to next stage | Stage status is `ready` |

### ActionSource Enum

| Value | Description |
|-------|-------------|
| `configured` | Action defined in process YAML (`expected_actions`) |
| `computed` | Action auto-generated by StageFlow based on evaluation |

### Action Priority

When a stage has `expected_actions` configured:
- **Only configured actions** are returned (as `execute_action` with source `configured`)
- Computed `resolve_validation` actions are suppressed

When a stage has **no** `expected_actions`:
- Computed actions are generated based on failed locks (`resolve_validation` with source `computed`)

### Computed Action Instructions

All computed actions now include helpful instructions:

- **PROVIDE_DATA**: "Add the '{property}' property to the element" (+ suggested value if available)
- **RESOLVE_VALIDATION**: "Update the '{property}' property to satisfy validation" (+ expected/current values)
- **TRANSITION**: "All requirements satisfied for stage '{stage_name}'" + "Proceed to next stage: '{next_stage}'"

See [ACTION_DESIGN_BEST_PRACTICES.md](ACTION_DESIGN_BEST_PRACTICES.md) for complete examples.

### Action Structure in Results

```python
# Example action in evaluation result
{
    "action_type": "provide_data",      # ActionType enum value
    "source": "computed",               # ActionSource enum value
    "description": "Provide required property 'email'",
    "related_properties": [],           # Properties related to this action
    "target_properties": ["email"],     # Properties to provide/modify
}

# Transition action (when ready)
{
    "action_type": "transition",
    "source": "computed",
    "description": "Ready to transition to 'profile_setup'",
    "related_properties": ["email", "verified"],  # Validated properties
    "target_properties": [],
    "target_stage": "profile_setup",    # Where to transition
    "gate_name": "email_verified",      # Gate that passed
}

# Configured action (from expected_actions)
{
    "action_type": "execute_action",
    "source": "configured",
    "description": "Verify your email address",
    "related_properties": ["email"],
    "target_properties": ["verified"],
    "name": "verify_email",             # From expected_actions
    "instructions": ["Check your inbox", "Click verification link"],
}
```

---

## Gate Object

A **Gate** defines a transition path from one stage to another. All locks must pass (AND logic).

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `target_stage` | string | ✓ | Destination stage if all locks pass |
| `locks` | array | ✓ | List of Lock objects (AND logic) |

### Specification

Gates are defined as a dictionary where the key is the gate name:

```yaml
gates:
  <gate_name>:                    # Gate identifier
    target_stage: <string>        # Required: Must exist in process stages
    locks:                        # Required: Array of Lock objects
      - <Lock>
```

### Multiple Gates (Branching Paths)

Stages can have multiple gates for different transition paths:

```yaml
gates:
  approve:
    target_stage: "approved"
    locks:
      - type: equals
        property_path: "review_status"
        expected_value: "approved"

  reject:
    target_stage: "rejected"
    locks:
      - type: equals
        property_path: "review_status"
        expected_value: "rejected"
```

---

## Lock Object

A **Lock** is a validation predicate that checks a condition on element data.

> **For complete lock type documentation:** See [Lock Types Reference](./LOCK_TYPES_REFERENCE.md)

### Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | string | ✓ | Lock type (e.g., `exists`, `equals`, `regex`) |
| `property_path` | string | ✓ | Property to validate |
| `expected_value` | any | | Expected value or criteria (type-dependent) |
| `error_message` | string | | Custom error message on failure |

### Full Format (Recommended)

```yaml
- type: <LOCK_TYPE>
  property_path: <string>
  expected_value: <any>
  error_message: <string>
```

### Shorthand Format

For `exists` locks only:

```yaml
- exists: "property.path"
  error_message: <string>
```

### Available Lock Types

| Category | Lock Types |
|----------|------------|
| **Existence** | `exists`, `not_empty` |
| **Comparison** | `equals`, `greater_than`, `less_than` |
| **Collections** | `in_list`, `not_in_list`, `contains` |
| **Patterns** | `regex` |
| **Type/Size** | `length`, `type_check`, `range` |
| **Logic** | `conditional`, `or_logic`, `or_group` |

---

## Property Path Notation

StageFlow supports flexible property access using dot and bracket notation.

### Syntax

```yaml
"email"                          # Simple property
"user.profile.name"              # Nested object (dot notation)
"items[0].status"                # Array access (bracket notation)
"user.orders[0].total"           # Mixed notation
"meta.workflow.steps[2].result"  # Deep nesting
```

### Length Functions

Use `length()` function for collection size checks:

```yaml
property_path: "length(items)"
```

---

## Complete Example

```yaml
process:
  name: document_approval
  description: "Document review and approval workflow"
  initial_stage: draft
  final_stage: approved
  stage_prop: "workflow.current_stage"
  regression_policy: "warn"

  stages:
    draft:
      name: "Draft"
      description: "Document is being written and edited before submission"
      fields:
        - title
        - content
        - author
      expected_actions:
        - name: "write_content"
          description: "Write and finalize document content"
          instructions:
            - "Add a descriptive title"
            - "Write the main content"
          related_properties:
            - "title"
            - "content"
      gates:
        submit_for_review:
          target_stage: review
          locks:
            - type: exists
              property_path: "title"
              error_message: "Document title is required"
            - type: not_empty
              property_path: "title"
              error_message: "Document title cannot be empty"

    review:
      name: "Review"
      description: "Document is under review by assigned reviewer"
      fields:
        - title
        - content
        - reviewer
        - review_status
      gates:
        approve:
          target_stage: approved
          locks:
            - type: equals
              property_path: "review_status"
              expected_value: "approved"
              error_message: "Document must be approved"

        request_changes:
          target_stage: draft
          locks:
            - type: equals
              property_path: "review_status"
              expected_value: "changes_requested"

    approved:
      name: "Approved"
      description: "Document has been approved for publication"
      fields:
        - title
        - content
        - approved_at
```
