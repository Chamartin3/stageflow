# StageFlow Process Design Guide

This guide teaches you how to design well-structured StageFlow processes by understanding the underlying principles, constraints, and validation rules.

---

## Table of Contents

- [Understanding Process Structure](#understanding-process-structure)
  - [The Directed Graph Model](#the-directed-graph-model)
  - [The Ideal Process Schema](#the-ideal-process-schema)
  - [System Constraints](#system-constraints)
- [The Three Guarantees](#the-three-guarantees)
  - [Reachability](#guarantee-1-reachability)
  - [Completability](#guarantee-2-completability)
  - [Determinism](#guarantee-3-determinism)
- [Schema Evolution and Mutations](#schema-evolution-and-mutations)
  - [Why Mutations Are Enforced](#why-mutations-are-enforced)
  - [How Schema Changes Are Expressed](#how-schema-changes-are-expressed)
  - [The Initial → Final Schema Transformation](#the-initial--final-schema-transformation)
- [Expected Actions](#expected-actions)
  - [Purpose](#purpose)
  - [Action Definition Structure](#action-definition-structure)
  - [Actions vs Locks](#actions-vs-locks)
  - [Constraint: Related Properties Must Be Validated](#constraint-related-properties-must-be-validated)
- [Validation Errors Reference](#validation-errors-reference)
  - [Gate-Level Errors](#gate-level-errors)
  - [Stage-Level Errors](#stage-level-errors)
  - [Graph-Level Errors](#graph-level-errors)
- [Design Checklist](#design-checklist)
- [Validation Commands](#validation-commands)

---

## Understanding Process Structure

### The Directed Graph Model

A StageFlow process models a **directed graph** where:

| Concept | Graph Term | Purpose |
|---------|------------|---------|
| **Stage** | Node | A state an element can be in |
| **Gate** | Edge | A transition between stages |
| **Lock** | Edge Weight | Conditions for traversing an edge |
| **Fields** | Node Properties | Data expected at that state |

The graph has exactly **one entry point** (initial stage) and exactly **one exit point** (final stage).

### The Ideal Process Schema

```yaml
process:
  name: my_workflow                    # REQUIRED: Unique identifier
  description: "My workflow"           # REQUIRED: Human-readable description
  initial_stage: start                 # REQUIRED: Entry point
  final_stage: completed               # REQUIRED: Exit point (exactly one)
  stage_prop: "current_stage"          # Optional: Auto-extract stage from element
  regression_policy: "warn"            # Optional: "ignore", "warn" (default), or "block"

  stages:
    # Initial stage - must have gates (entry point needs exits)
    start:
      name: "Start"
      description: "User begins the workflow"
      fields:                          # Data expected at this stage
        - email
        - password
      expected_actions:                # Guidance for progressing through this stage
        - description: "Provide valid email and password"
          name: "credentials_input"
          instructions:
            - "Enter a valid email address"
            - "Create a strong password (8+ characters)"
          related_properties:
            - "email"
            - "password"
      gates:                           # Transitions out of this stage
        proceed:
          target_stage: processing
          locks:                       # Conditions to pass (AND logic)
            - exists: "email"
            - type: regex
              property_path: "email"
              expected_value: "^.+@.+$"

    # Intermediate stage - transforms data
    processing:
      name: "Processing"
      fields:
        - email
        - status
      expected_actions:
        - description: "Complete processing task"
          related_properties:
            - "status"
      gates:
        complete:
          target_stage: completed
          locks:
            - type: equals
              property_path: "status"
              expected_value: "done"

    # Final stage - NO gates allowed (terminal)
    completed:
      name: "Completed"
      fields:
        - email
        - status
        - completion_date
      expected_actions: []             # Final stages typically have no actions
      # No gates section - final stages are terminal
```

### System Constraints

StageFlow enforces these **hard constraints**:

| Constraint | Reason |
|------------|--------|
| **Exactly one initial stage** | Elements need a defined entry point |
| **Exactly one final stage** | Elements need a defined completion point |
| **Final stage has no gates** | Terminal stages cannot have outgoing transitions |
| **All stages must be reachable** | Unreachable stages are dead code |
| **All stages must reach final** | Elements must be able to complete |
| **No self-referencing gates** | Immediate infinite loops are invalid |
| **No duplicate gate targets** | Each stage can have at most one gate per target |
| **Gates must transform schema** | Transitions must represent meaningful change |

---

## The Three Guarantees

StageFlow validates your process to ensure three fundamental guarantees:

### Guarantee 1: Reachability

> **Every stage must be reachable from the initial stage.**

A stage that can't be reached is dead code—it exists but serves no purpose. The system performs a breadth-first search from the initial stage to verify all stages are connected.

**Why it matters:** Unreachable stages indicate process design errors, typos in target_stage references, or orphaned logic that should be removed.

### Guarantee 2: Completability

> **Every stage must have a path to the final stage.**

An element entering any stage must eventually be able to complete the process. No element should get "stuck" in a state with no way forward.

**Why it matters:** Dead-end stages trap elements forever, preventing process completion and potentially causing resource leaks or business logic failures.

### Guarantee 3: Determinism

> **Transitions must be unambiguous and finite.**

The process must:
1. Know which gate to evaluate (no duplicate targets)
2. Have satisfiable lock conditions (no logical contradictions)
3. Terminate cycles (no infinite loops)

**Why it matters:** Ambiguous transitions make the process behavior unpredictable. Infinite loops consume resources indefinitely.

---

## Schema Evolution and Mutations

### Why Mutations Are Enforced

StageFlow tracks **schema evolution** through stages. Each stage defines an `initial_schema` (the `fields` section) and each gate produces a `final_schema` (fields + lock requirements).

**The core principle:** A gate transition should represent meaningful data change.

If a gate doesn't transform the schema, it means:
- The element already has all required properties
- The gate is redundant or incorrectly designed
- The lock conditions don't require new data

This is flagged as `EMPTY_STAGE_TRANSFORMATION` (warning).

### How Schema Changes Are Expressed

Schema mutations happen through two mechanisms:

#### 1. Stage Fields (Initial Schema)

Fields declared in a stage define the **initial schema**—properties an element should have when **entering** the stage. Fields do **not** need to include all properties that will be evaluated; locks add additional requirements.

```yaml
profile_setup:
  fields:
    - email           # Expected on entry
    - name            # Expected on entry
  gates:
    complete:
      target_stage: active
      locks:
        - exists: "bio"        # Added by lock - not in fields
        - exists: "avatar_url" # Added by lock - not in fields
```

**Initial schema:** `{email, name}`
**Final schema:** `{email, name, bio, avatar_url}` (fields + lock requirements)

Fields support three syntax levels:

```yaml
fields:
  - email                    # Level 1: Simple list (string type implied)
  - name

fields:
  email: string              # Level 2: Type shortcuts
  age: int

fields:
  age:                       # Level 3: Full specs with constraints
    type: int
    min: 18
```

#### 2. Lock Requirements (Implicit Schema)

Locks implicitly require properties to exist:

```yaml
gates:
  complete:
    target_stage: active
    locks:
      - exists: "verified_at"          # Adds: verified_at must exist
      - type: equals
        property_path: "status"        # Adds: status must exist and equal "active"
        expected_value: "active"
      - type: greater_than
        property_path: "score"         # Adds: score must exist and be > 50
        expected_value: 50
```

### The Initial → Final Schema Transformation

For each stage, StageFlow computes:

```
initial_schema = fields defined in stage
final_schema = initial_schema + properties required by gate locks
```

**Valid transformation:**
```yaml
# Initial: {email, password}
# Final: {email, password, verified_at, status}  ← Added by locks

registration:
  fields: [email, password]
  gates:
    verify:
      target_stage: active
      locks:
        - exists: "verified_at"        # Adds verified_at
        - type: equals
          property_path: "status"
          expected_value: "verified"   # Adds status
```

**Invalid transformation (warning):**
```yaml
# Initial: {email, password, status}
# Final: {email, password, status}  ← No change!

registration:
  fields: [email, password, status]  # status already in fields
  gates:
    proceed:
      target_stage: next
      locks:
        - exists: "status"             # status already exists - no mutation
```

---

## Expected Actions

Expected actions provide **user-facing guidance** for progressing through a stage. They are documentation and UX helpers—not validation rules.

### Purpose

| Aspect | Description |
|--------|-------------|
| **User Guidance** | Tell users what they need to do to progress |
| **Documentation** | Explain business logic and requirements |
| **UI Integration** | Power progress indicators and help text |
| **Property Mapping** | Link actions to specific data fields |

### Action Definition Structure

```yaml
expected_actions:
  - description: "Brief summary of the action"     # REQUIRED
    name: "action_identifier"                      # Optional: unique ID
    instructions:                                  # Optional: step-by-step guide
      - "Step 1: Do this"
      - "Step 2: Then do that"
    related_properties:                            # Optional: input/context properties
      - "property_path"
    target_properties:                             # Optional: output/result properties
      - "property_path"
```

### Related vs Target Properties

Understanding the difference is crucial for clear action design:

| Property Type | Purpose | Example |
|---------------|---------|---------|
| **`related_properties`** | Properties used as **input** to execute the action | `email` (needed to send verification) |
| **`target_properties`** | Properties that **capture the result** of the action | `verified`, `verified_at` (set after completion) |

**Example:**
```yaml
expected_actions:
  - name: "upload_document"
    description: "Upload identity document for verification"
    instructions:
      - "Take a photo of your government ID"
      - "Upload the image file"
    related_properties:
      - "user_id"           # Input: identifies which user
      - "document_type"     # Input: determines expected format
    target_properties:
      - "document_url"      # Output: where document was uploaded
      - "document_status"   # Output: processing status
```

### Example: Multi-Action Stage

```yaml
checkout:
  name: "Checkout"
  description: "Complete purchase with shipping and payment"
  fields:
    - cart_items
    - shipping_address
    - payment_method
  expected_actions:
    - description: "Enter shipping address"
      name: "shipping"
      instructions:
        - "Provide complete street address"
        - "Include apartment/unit number if applicable"
        - "Verify ZIP code matches city"
      related_properties:
        - "shipping_address"
        - "shipping_address.zip"

    - description: "Select payment method"
      name: "payment"
      instructions:
        - "Choose credit card or PayPal"
        - "Verify billing address matches card"
      related_properties:
        - "payment_method"

  gates:
    complete_checkout:
      target_stage: confirmation
      locks:
        - exists: "shipping_address"
        - exists: "payment_method"
```

### Actions vs Locks

| Aspect | Expected Actions | Locks |
|--------|-----------------|-------|
| **Purpose** | User guidance | Validation enforcement |
| **Effect** | Documentation only | Blocks/allows transitions |
| **Failure** | No effect on flow | Prevents gate passage |
| **Visibility** | Shown to users | Internal logic |

**Key insight:** Actions tell users *what to do*. Locks verify *that it was done*.

### Action Types in Evaluation Results

When you evaluate an element, StageFlow returns actions with specific types:

| ActionType | Source | When Generated |
|------------|--------|----------------|
| `provide_data` | `computed` | Status is `incomplete` - missing required fields |
| `resolve_validation` | `computed` | Status is `blocked` - failed locks (no configured actions) |
| `execute_action` | `configured` | Status is `blocked` - from stage's `expected_actions` |
| `transition` | `computed` | Status is `ready` - can move to next stage |

**Priority Rule:** If a stage has `expected_actions`, only those are returned (as `execute_action`). Computed `resolve_validation` actions are suppressed to avoid duplication.

### Constraint: Related Properties Must Be Validated

**Every property listed in `related_properties` must be tested by at least one gate lock.**

This ensures consistency between what users are told to do and what the system actually validates.

```yaml
# ❌ INVALID: related_properties not tested by any lock
checkout:
  expected_actions:
    - description: "Enter promo code"
      related_properties:
        - "promo_code"              # Listed but never validated!
  gates:
    complete:
      target_stage: done
      locks:
        - exists: "payment_method"  # promo_code not checked

# ✅ VALID: All related_properties have corresponding locks
checkout:
  expected_actions:
    - description: "Enter promo code"
      related_properties:
        - "promo_code"
  gates:
    complete:
      target_stage: done
      locks:
        - exists: "payment_method"
        - exists: "promo_code"      # Now validated
```

**Why this matters:** If an action tells users to provide data that is never validated, the action is misleading. Either remove the property from `related_properties` or add a lock that tests it.

---

## Validation Errors Reference

### Gate-Level Errors

These errors are detected when analyzing individual gates.

#### Self-Referencing Gate

**Severity:** Fatal
**Violates:** Determinism (creates degenerate cycle)

A gate's `target_stage` points to its own containing stage.

```yaml
# ❌ INVALID: Immediate infinite loop
processing:
  gates:
    retry: { target_stage: processing }  # Points to itself!
```

```yaml
# ✅ VALID: Use intermediate stage for retry logic
processing:
  gates:
    retry: { target_stage: retry_queue }

retry_queue:
  gates:
    back:
      target_stage: processing
      locks:
        - type: less_than
          property_path: "attempt_count"
          expected_value: 5
```

#### Logical Conflict

**Severity:** Fatal
**Violates:** Determinism (unsatisfiable conditions)

Locks within a single gate have contradictory conditions.

**Conflicting EQUALS values:**
```yaml
# ❌ INVALID: status can't be both values simultaneously
locks:
  - type: equals
    property_path: "status"
    expected_value: "active"
  - type: equals
    property_path: "status"
    expected_value: "pending"
```

**Impossible numeric range:**
```yaml
# ❌ INVALID: No number is > 100 AND < 50
locks:
  - type: greater_than
    property_path: "score"
    expected_value: 100
  - type: less_than
    property_path: "score"
    expected_value: 50

# ✅ VALID: Coherent range (50 < score < 100)
locks:
  - type: greater_than
    property_path: "score"
    expected_value: 50
  - type: less_than
    property_path: "score"
    expected_value: 100
```

**EQUALS vs bounds conflict:**
```yaml
# ❌ INVALID: score can't equal 30 AND be > 50
locks:
  - type: equals
    property_path: "score"
    expected_value: 30
  - type: greater_than
    property_path: "score"
    expected_value: 50
```

---

### Stage-Level Errors

These errors are detected when analyzing a stage and its gates collectively.

#### Empty Stage Transformation

**Severity:** Warning
**Meaning:** Gate doesn't meaningfully change the schema

```yaml
# ⚠️ WARNING: Gate locks don't add new requirements
checkout:
  fields: [cart_items, total, payment_method]
  gates:
    pay:
      target_stage: payment
      locks:
        - exists: "total"  # Already in fields - no transformation
```

```yaml
# ✅ VALID: Gate adds new schema requirements
checkout:
  fields: [cart_items, total]
  gates:
    pay:
      target_stage: payment
      locks:
        - exists: "payment_method"     # Adds payment_method
        - type: greater_than
          property_path: "total"
          expected_value: 0
```

#### Multiple Gates Same Target

**Severity:** Fatal
**Violates:** Determinism (ambiguous transition)

Two or more gates in the same stage point to the same target stage.

```yaml
# ❌ INVALID: Which gate's locks should be evaluated?
checkout:
  gates:
    credit_card:
      target_stage: payment            # Same target
      locks: [...]
    paypal:
      target_stage: payment            # Same target
      locks: [...]
```

```yaml
# ✅ VALID: Single gate with OR logic
checkout:
  gates:
    pay:
      target_stage: payment
      locks:
        - type: or_logic
          paths:
            - locks: [{ exists: "credit_card" }]
            - locks: [{ exists: "paypal_email" }]
```

#### Duplicate Gate Schemas

**Severity:** Fatal
**Meaning:** Two gates produce identical final schemas

```yaml
# ❌ INVALID: Both gates result in same schema transformation
processing:
  fields: [data]
  gates:
    path_a:
      target_stage: review
      locks:
        - exists: "validated"
    path_b:
      target_stage: archive
      locks:
        - exists: "validated"  # Same lock, same schema change
```

---

### Graph-Level Errors

These errors are detected when analyzing the process structure as a whole.

#### Unreachable Stage

**Severity:** Fatal
**Violates:** Guarantee 1 (Reachability)

A stage cannot be reached from the initial stage via any gate path.

```yaml
# ❌ INVALID: special_case has no incoming edges
initial_stage: start
stages:
  start:
    gates:
      next: { target_stage: end }
  special_case:                        # No gate points here!
    gates:
      done: { target_stage: end }
  end: {}
```

```yaml
# ✅ VALID: All stages are reachable
stages:
  start:
    gates:
      next: { target_stage: end }
      special: { target_stage: special_case }  # Now reachable
  special_case:
    gates:
      done: { target_stage: end }
  end: {}
```

#### Dead-End Stage

**Severity:** Warning
**Violates:** Guarantee 2 (Completability)

A non-final stage has no path (direct or through other stages) to the final stage.

```yaml
# ❌ INVALID: waiting has no exit path
stages:
  start:
    gates:
      wait: { target_stage: waiting }
  waiting: {}                          # No gates! Elements stuck forever
  end: {}
```

```yaml
# ✅ VALID: All stages can reach final
stages:
  start:
    gates:
      wait: { target_stage: waiting }
  waiting:
    gates:
      continue: { target_stage: end }  # Exit path exists
  end: {}
```

#### Orphaned Stage

**Severity:** Warning
**Meaning:** Stage has no gates, is not final, and is not referenced

```yaml
# ⚠️ WARNING: abandoned is completely disconnected
stages:
  start:
    gates:
      next: { target_stage: end }
  abandoned:                           # No gates, not final, not targeted
    fields: [data]
  end: {}
```

#### Final Stage Has Gates

**Severity:** Fatal
**Violates:** System constraint (final is terminal)

The designated final stage has outgoing transitions.

```yaml
# ❌ INVALID: Final stage cannot have transitions
final_stage: completed
stages:
  completed:
    gates:
      reopen: { target_stage: processing }  # Not allowed!
```

```yaml
# ✅ VALID: Final stage is terminal
final_stage: completed
stages:
  completed:
    fields: [completion_date]
    # No gates - this is terminal
```

#### Infinite Cycle

**Severity:** Fatal
**Violates:** Guarantee 2 (Completability)

A cycle exists with no exit path to the final stage from any stage in the cycle.

```yaml
# ❌ INVALID: A ↔ B forms closed loop, no exit to end
stages:
  a:
    gates:
      to_b: { target_stage: b }
  b:
    gates:
      to_a: { target_stage: a }
  end: {}                              # Unreachable from cycle!
```

```yaml
# ✅ VALID: Cycle has exit path
stages:
  a:
    gates:
      to_b: { target_stage: b }
  b:
    gates:
      to_a: { target_stage: a }
      finish: { target_stage: end }    # Exit from cycle
  end: {}
```

#### Uncontrolled Cycle

**Severity:** Warning
**Violates:** Guarantee 3 (Determinism)

A cycle has an exit path but no detectable termination condition in locks.

```yaml
# ⚠️ WARNING: Exit exists but nothing guarantees termination
processing:
  gates:
    retry: { target_stage: processing }  # Could loop forever
    done: { target_stage: end }
```

**Solution patterns:**

```yaml
# Pattern 1: Counter-based termination
retry:
  target_stage: processing
  locks:
    - type: less_than
      property_path: "attempt_count"
      expected_value: 5

# Pattern 2: Boolean flag termination
retry:
  target_stage: processing
  locks:
    - type: equals
      property_path: "needs_retry"
      expected_value: true
done:
  target_stage: end
  locks:
    - type: equals
      property_path: "needs_retry"
      expected_value: false

# Pattern 3: Status progression
continue:
  target_stage: processing
  locks:
    - type: in_list
      property_path: "status"
      expected_value: ["pending", "retrying"]
complete:
  target_stage: end
  locks:
    - type: equals
      property_path: "status"
      expected_value: "done"
```

---

## Design Checklist

Before deploying a process, verify:

### Structure
- [ ] `initial_stage` is defined and exists in stages
- [ ] `final_stage` is defined and exists in stages
- [ ] Final stage has no `gates` section
- [ ] All stage IDs are unique

### Connectivity
- [ ] Every stage is reachable from initial (except initial itself)
- [ ] Every stage can reach final (except final itself)
- [ ] No orphaned stages (no gates, not final, not targeted)

### Gates
- [ ] No gate targets its own stage (self-reference)
- [ ] Each stage has at most one gate per target
- [ ] Gate locks don't have logical contradictions
- [ ] Gates transform the schema (add or modify properties)

### Cycles
- [ ] Every cycle has an exit path to final
- [ ] Cycle exit conditions are detectable (counters, flags, status)

### Locks
- [ ] Lock `property_path` values exist or are added by the transition
- [ ] Numeric comparisons have valid ranges
- [ ] `expected_value` types match the lock type

---

## Validation Commands

```bash
# Validate and view process structure
uv run stageflow process view your_process.yaml

# Verbose output shows all detected issues
uv run stageflow -v process view your_process.yaml

# Load from registry
uv run stageflow process view @my_process

# Generate visual diagram
uv run stageflow process diagram your_process.yaml -o diagram.md
```

StageFlow will report all violations by severity level:
- **FATAL**: Process cannot be loaded
- **WARNING**: Process loads but may have issues
- **INFO**: Informational (e.g., controlled cycles detected)
