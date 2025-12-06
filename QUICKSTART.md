# Quickstart
A no-nonsense guide to get you building processes quickly.

---

## The 5-Minute Mental Model

Think of it like a **flowchart**:

```
[Start] --gate--> [Middle] --gate--> [End]
```

- **Stage** = A box in the flowchart (a state your data can be in)
- **Gate** = An arrow between boxes (how data moves forward)
- **Lock** = Conditions on the arrow (what must be true to move)
- **Element** = Your data being evaluated

---

## Your First Process (Copy-Paste This)

```yaml
process:
  name: simple_approval
  description: "Document goes from draft to approved"
  initial_stage: draft
  final_stage: approved

  stages:
    draft:
      name: "Draft"
      description: "Document is being written"

      # Fields = Initial Schema (what exists when entering this stage)
      fields:
        title:
          type: string
          description: "Document title"
        content:
          type: string
          description: "Document body"

      # Expected Actions = What user must do to progress
      expected_actions:
        - name: "write_document"
          description: "Write the document content"
          instructions:
            - "Add a descriptive title"
            - "Write the main content"
            - "Review for errors before submitting"
          related_properties:
            - "title"
            - "content"

      gates:
        submit:
          target_stage: approved
          locks:
            - exists: "title"
              error_message: "Document needs a title"
            - exists: "content"
              error_message: "Document needs content"
            - type: not_empty
              property_path: "title"
              error_message: "Title cannot be empty"

    approved:
      name: "Approved"
      description: "Document has been approved"
      fields:
        title:
          type: string
        content:
          type: string
        approved_at:
          type: string
          format: date-time
```

Test it:
```bash
uv run stageflow process view my_process.yaml
```

---

## The Three Golden Rules

### 1. Every Stage Needs a Way Out (except final)

```yaml
# BAD: Stuck forever
review:
  fields: [data]
  # No gates! Where does data go?

# GOOD: Has exit
review:
  fields: [data]
  gates:
    approve: { target_stage: done, locks: [...] }
```

### 2. Final Stage = No Gates

```yaml
# BAD: Final can't have exits
final_stage: completed
stages:
  completed:
    gates:  # ERROR! Final stage can't have gates
      restart: { target_stage: start }

# GOOD: Final is terminal
completed:
  fields: [result]
  # No gates section
```

### 3. All Paths Lead to Final

```yaml
# BAD: orphan stage
start --> middle --> end
           orphan (unreachable!)

# GOOD: All connected
start --> middle --> end
            |          ^
            +--review--+
```

---

## Stages Cheatsheet

```yaml
stage_id:                    # Use snake_case
  name: "Display Name"       # Human-readable
  description: "What happens here"

  fields:                    # INITIAL SCHEMA: what data exists when entering this stage
    - simple_field
    - nested.path

  expected_actions:          # IMPORTANT: What user must do to progress
    - name: "do_thing"
      description: "Fill in the form"
      instructions:
        - "Step 1"
        - "Step 2"
      related_properties:
        - field_name

  gates:                     # Exits (ALL conditions must pass)
    gate_name:
      target_stage: next_stage
      locks: [...]
```

---

## Fields = Initial Schema (Important!)

Fields define the **initial schema** - what properties exist when an element **enters** the stage. Gates add additional requirements through locks.

### Three Ways to Define Fields

```yaml
# Level 1: Simple list (just names, type inferred)
fields:
  - email
  - name

# Level 2: Type shortcuts
fields:
  email: string
  age: int
  active: bool

# Level 3: Full schemas (RECOMMENDED for production)
fields:
  email:
    type: string
    format: email
  age:
    type: integer
    minimum: 0
  profile:
    type: object
    properties:
      name:
        type: string
      bio:
        type: string
```

**Why use full schemas?**
- Better validation error messages
- Self-documenting process definitions
- Enables JSON Schema generation (`stageflow process schema`)
- Catches data issues early

### Schema Evolution Through Stages

```yaml
registration:           # Initial schema: {email, password}
  fields:
    email: string
    password: string
  gates:
    verify:
      target_stage: profile_setup
      locks:
        - exists: "verified_at"     # Lock ADDS this requirement

profile_setup:          # Initial schema: {email, password, verified_at, name}
  fields:
    email: string
    password: string
    verified_at: string
    name: string        # New field expected at this stage
```

---

## Expected Actions (Don't Skip These!)

Expected actions tell users **what they need to do** to progress. They're essential for good UX.

### Why They Matter

| Without Actions | With Actions |
|-----------------|--------------|
| User sees "blocked" status | User sees "Upload your ID document" |
| No guidance | Step-by-step instructions |
| Frustrating experience | Clear path forward |

### Action Structure

```yaml
expected_actions:
  - name: "upload_document"              # Unique identifier
    description: "Upload ID document"    # Brief summary (REQUIRED)
    instructions:                        # Step-by-step guidance
      - "Take a clear photo of your ID"
      - "Ensure all text is readable"
      - "File must be PNG or JPG, under 5MB"
    related_properties:                  # Input: properties needed to execute action
      - "user_id"
      - "document_type"
    target_properties:                   # Output: properties that capture the result
      - "document_url"
      - "upload_status"
```

### Related vs Target Properties

| Property | Purpose | Think of it as... |
|----------|---------|-------------------|
| `related_properties` | Properties needed to **execute** the action | **Input** (context/dependencies) |
| `target_properties` | Properties that **capture the result** | **Output** (what gets set) |

### Rule: Related Properties Must Be Validated

**Every property in `related_properties` MUST have a corresponding lock.**

```yaml
# BAD: Tells user to provide promo_code but never checks it
expected_actions:
  - description: "Enter promo code"
    related_properties:
      - "promo_code"           # Listed but not validated!
gates:
  checkout:
    locks:
      - exists: "payment"      # promo_code not checked

# GOOD: Action and validation aligned
expected_actions:
  - description: "Enter promo code"
    related_properties:
      - "promo_code"
gates:
  checkout:
    locks:
      - exists: "payment"
      - exists: "promo_code"   # Now validated!
```

### Complete Stage Example

```yaml
identity_verification:
  name: "Identity Verification"
  description: "User verifies their identity with government ID"

  fields:
    email:
      type: string
      format: email
    user_id:
      type: string

  expected_actions:
    - name: "upload_id"
      description: "Upload government-issued ID"
      instructions:
        - "Use passport, driver's license, or national ID"
        - "Ensure photo is clear and all corners visible"
        - "File size must be under 10MB"
      related_properties:
        - "id_document_url"
        - "id_document_type"

    - name: "selfie_verification"
      description: "Take a selfie for face matching"
      instructions:
        - "Ensure good lighting"
        - "Face the camera directly"
        - "Remove glasses and hats"
      related_properties:
        - "selfie_url"

  gates:
    verify:
      target_stage: verified
      locks:
        - exists: "id_document_url"
        - exists: "id_document_type"
        - type: in_list
          property_path: "id_document_type"
          expected_value: ["passport", "drivers_license", "national_id"]
        - exists: "selfie_url"
```

---

## Gates Cheatsheet

```yaml
gates:
  gate_name:
    target_stage: where_to_go
    locks:           # ALL must pass (AND logic)
      - lock1
      - lock2
```

**Multiple gates = multiple paths:**
```yaml
gates:
  approve:
    target_stage: approved
    locks:
      - type: equals
        property_path: "decision"
        expected_value: "approve"

  reject:
    target_stage: rejected
    locks:
      - type: equals
        property_path: "decision"
        expected_value: "reject"
```

---

## Locks Cheatsheet

### The Most Common Locks

```yaml
# Property must exist
- exists: "email"

# Property not empty
- type: not_empty
  property_path: "name"

# Exact value match
- type: equals
  property_path: "status"
  expected_value: "active"

# In allowed list
- type: in_list
  property_path: "role"
  expected_value: ["admin", "user"]
```

### Comparison Locks

```yaml
- type: greater_than
  property_path: "age"
  expected_value: 18

- type: less_than
  property_path: "qty"
  expected_value: 100

- type: range
  property_path: "score"
  expected_value: [0, 100]
```

### Pattern Locks

```yaml
- type: regex
  property_path: "email"
  expected_value: "^.+@.+$"
  error_message: "Invalid email"

- type: length
  property_path: "code"
  expected_value: 6
```

### OR Logic (one of these must pass)

```yaml
- type: or_logic
  paths:
    - locks:
        - type: equals
          property_path: "verified_email"
          expected_value: true
    - locks:
        - type: equals
          property_path: "verified_phone"
          expected_value: true
```

---

## Common Patterns

### Linear Flow
```
[start] --> [middle] --> [end]
```

### Branching
```
           +--> [approved]
[review] --+
           +--> [rejected]
```

### Retry Loop (with limit!)
```yaml
processing:
  gates:
    retry:
      target_stage: processing
      locks:
        - type: less_than
          property_path: "attempts"
          expected_value: 3
    complete:
      target_stage: done
      locks:
        - type: equals
          property_path: "status"
          expected_value: "success"
```

---

## Always Add Error Messages

```yaml
# BAD: Confusing for users
- type: regex
  property_path: "phone"
  expected_value: "^\\d{10}$"

# GOOD: Helpful
- type: regex
  property_path: "phone"
  expected_value: "^\\d{10}$"
  error_message: "Phone must be 10 digits (e.g., 5551234567)"
```

---

## Validation Commands

```bash
# Check process
uv run stageflow process view process.yaml

# Create new process from template
uv run stageflow process new my_process.yaml

# Visualize
uv run stageflow process diagram process.yaml -o diagram.md

# Test with data
echo '{"email": "test@example.com"}' | uv run stageflow evaluate process.yaml
```

---

## The 3 Stage Statuses

| Stage Status | Meaning | What to Do |
|--------------|---------|------------|
| `incomplete` | Missing required properties | Add the missing data |
| `blocked` | Has properties but fails locks | Complete the required actions |
| `ready` | All locks pass | Can move to next stage |

---

## Action Types in Results

When you evaluate an element, you get **actions** telling you what to do:

| ActionType | Source | When You See It |
|------------|--------|-----------------|
| `provide_data` | `computed` | Missing required field (`incomplete` status) |
| `resolve_validation` | `computed` | Failed gate lock (`blocked` status, no configured actions) |
| `execute_action` | `configured` | From stage's `expected_actions` (`blocked` status) |
| `transition` | `computed` | Ready to move forward (`ready` status) |

**Key insight:** If you define `expected_actions` in your stage, those take priority and are returned as `execute_action`. Otherwise, StageFlow auto-generates `resolve_validation` actions from failed locks.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Final stage has gates | Remove the gates section |
| Stage has no exit | Add a gate or make it final |
| Stage is unreachable | Add a gate pointing to it |
| Infinite loop | Add counter/boolean exit condition |
| Two gates same target | Use OR logic in single gate |
| No error messages | Add `error_message` to locks |
| Missing expected_actions | Add actions with instructions for user guidance |
| Simple field lists | Use full schemas with types for better validation |
| related_properties not validated | Ensure every related_property has a lock |

---

## Next Steps

For the full details, see:
- `docs/PROCESS_DESIGN_GUIDE.md` - Complete design principles
- `docs/LOCK_TYPES_REFERENCE.md` - All lock types explained
- `examples/` - Real-world examples

```bash
# Browse examples
ls examples/process_validation/valid_processes/
```
