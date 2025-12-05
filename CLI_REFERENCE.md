# StageFlow CLI Reference

## What is StageFlow?

StageFlow is a **declarative multi-stage validation framework** that helps you define and enforce workflows for data validation and progression. Instead of writing complex validation logic in code, you define your process stages and rules in YAML/JSON configuration files. StageFlow then evaluates where your data stands in the workflow without modifying it.

**Key Benefits:**
- **Declarative**: Define validation rules as configuration, not code
- **Non-mutating**: Framework never modifies your data
- **Auditable**: All validation logic is visible and traceable
- **Reusable**: Same process definitions work across different applications

**Common Use Cases:**
- User onboarding workflows (email verification → profile setup → active user)
- Document approval processes (draft → review → approved → published)
- Order fulfillment pipelines (cart → payment → processing → shipped)
- Data pipeline validation stages
---

## Breaking Changes (v2.0.0)

**Command Structure Reorganization**

As of StageFlow v2.0.0, process-related commands have been reorganized under a unified `process` parent command for better organization and scalability.

### Old Command Structure (v1.x)
```bash
stageflow view <process>           # View process details
stageflow new <name>               # Create new process
stageflow diagram <process>        # Generate diagram
stageflow reg <subcommand>         # Registry commands
stageflow evaluate <process> -e <element>  # Element evaluation
```

### New Command Structure (v2.0.0)
```bash
stageflow process view <process>      # View process details
stageflow process new <name>          # Create new process
stageflow process diagram <process>   # Generate diagram
stageflow process registry <subcommand>  # Registry commands
stageflow evaluate <process> -e <element>  # Element evaluation (unchanged)
```

### Migration Guide
- Replace `stageflow view` with `stageflow process view`
- Replace `stageflow new` with `stageflow process new`
- Replace `stageflow diagram` with `stageflow process diagram`
- Replace `stageflow reg` with `stageflow process registry`
- The `evaluate` command remains at the top level (no change needed)

---

## Core Commands

### 1. Process View

Display comprehensive information about a process definition including stages, transitions, and validation status.

```bash
# View a process file
stageflow process view process.yaml

# View from registry (using @ prefix)
stageflow process view @user_onboarding

# JSON output for API integration
stageflow process view process.yaml --json
```

**Example Output:**
```
✅ Process: user_registration
   Description: User onboarding workflow
   Valid: Yes

   📊 Process Structure:
   ├─ email_signup (initial)
   │  → email_verified gate → profile_setup
   ├─ profile_setup
   │  → profile_complete gate → active_user
   └─ active_user (final)
```

---

### 2. Evaluate Element Against Process

Assess where an element (data) stands in a multi-stage process and determine what actions are needed.

```bash
# Evaluate element (stage auto-detected from element if stage_prop configured)
stageflow evaluate process.yaml --element data.json

# Evaluate at specific stage (overrides auto-detection)
stageflow evaluate process.yaml -e data.json -s profile_setup

# Verbose output with stage selection details
stageflow evaluate process.yaml -e data.json -v

# JSON output
stageflow evaluate process.yaml -e data.json --json

# Read element from stdin
cat data.json | stageflow evaluate process.yaml
```

**Stage Selection Priority:**
1. **Explicit `-s` flag** (highest priority) - overrides everything
2. **Auto-detection** - uses `stage_prop` from process config to extract stage from element data
3. **Default** (lowest priority) - uses process `initial_stage`

**Example Output:**
```
📍 Current Stage: email_signup
Status: blocked

🔒 Gate: email_verified (Target: profile_setup)
   Status: ❌ Not passed

   Actions:
   • [execute_action] Verify your email address
   • [provide_data] Add property 'meta.email_verified_at'

⚠️ Regression: No backward progression detected
```

**Action Types in Results:**

| ActionType | Source | Description |
|------------|--------|-------------|
| `provide_data` | `computed` | Missing required field (status: `incomplete`) |
| `resolve_validation` | `computed` | Failed gate lock (status: `blocked`, no configured actions) |
| `execute_action` | `configured` | From stage's `expected_actions` (status: `blocked`) |
| `transition` | `computed` | Ready to move (status: `ready`) |

**Element File Example (data.json):**
```json
{
  "email": "john@example.com",
  "profile": {
    "first_name": "John"
  }
}
```

---

### 3. Process New

Generate a new process file from predefined templates.

```bash
# Create basic process
stageflow process new my_process.yaml

# Create without extension (automatically adds .yaml)
stageflow process new approval_workflow

# Create from specific template
stageflow process new document_flow --template approval

# Available templates: basic, approval
```

**Example Output:**
```
✅ Process 'my_process' created at my_process.yaml
   Template: basic
   Stages: 3

💡 Use 'stageflow process view my_process.yaml' to view the new process
```

---

### 4. Process Diagram

Create a visual representation of your process flow using Mermaid diagrams.

```bash
# Generate diagram (auto-names as process.diagram.md)
stageflow process diagram process.yaml

# Specify output file
stageflow process diagram process.yaml -o workflow.md

# Diagram from registry
stageflow process diagram @user_onboarding -o onboarding_flow.md

# JSON output
stageflow process diagram process.yaml --json
```

**Example Output:**
```
✅ Mermaid visualization written to process.diagram.md
```

The generated Markdown file contains a Mermaid diagram that can be rendered in GitHub, GitLab, or any Markdown viewer that supports Mermaid.

---

### 5. Process Schema

Generate JSON Schema (Draft-07) from StageFlow process definitions to validate element structure.

```bash
# Generate cumulative schema (default - includes all properties from initial to target stage)
stageflow process schema process.yaml review

# Generate stage-specific schema (only properties for target stage)
stageflow process schema process.yaml review --stage-specific

# Save schema to file
stageflow process schema process.yaml review -o schema.yaml

# Get JSON output for machine processing
stageflow process schema process.yaml review --json

# Combine options
stageflow process schema @my_process final -s -o final_schema.json
```

**Parameters:**
- `PROCESS_SOURCE`: Process file path or `@registry_name`
- `TARGET_STAGE`: Target stage name for schema generation

**Options:**
- `--stage-specific, -s`: Generate schema for target stage only (default: cumulative)
- `--output, -o PATH`: Output file path (default: stdout)
- `--json`: Output in JSON format (default: YAML)

**Modes:**

**Cumulative Mode (default):**
- Merges schemas from all stages in path from initial to target
- Later stages override earlier stages for duplicate properties
- Required fields include EXISTS locks from all stages in path

**Stage-Specific Mode (--stage-specific):**
- Uses only target stage's expected_properties
- Required fields include only EXISTS locks from target stage
- Useful for validating stage-specific changes

**Example Output (YAML):**
```yaml
$schema: http://json-schema.org/draft-07/schema#
title: user_onboarding - Verification (Cumulative)
description: 'Schema for stage: Verification'
type: object
properties:
  email:
    type: string
  user_id:
    type: string
  verification:
    type: string
required:
  - email
  - verification
```

**Error Handling:**
- **Invalid process source:** Process file not found or invalid format
- **Non-existent stage:** Target stage doesn't exist in process
- **Unreachable stage:** No path from initial stage to target stage

---

## Registry Commands

The registry allows you to manage a collection of process definitions in a central directory. Use the `@` prefix to reference registry processes.

### Configuration

Set the registry directory using environment variables:

```bash
export STAGEFLOW_PROCESSES_DIR="./processes"
export STAGEFLOW_DEFAULT_FORMAT="yaml"
```

### 5. Process Registry List

Display all processes in the registry with their status and details.

```bash
# List all registry processes
stageflow process registry list

# JSON output
stageflow process registry list --json
```

**Example Output:**
```
📂 Registry Processes (3 found)
   Registry directory: /home/user/stageflow/processes

├─ ✅ @customer_journey
   Name: Customer Lifecycle Management
   Stages: 5

├─ ✅ @user_onboarding
   Name: User Registration and Onboarding
   Stages: 4

└─ ❌ @approval_workflow
   Name: Document Approval Process
   Issues: 2 consistency problems

💡 Use 'stageflow process view @process_name' to inspect a specific process
```

---

### 6. Process Registry Import

Add a process file to the registry for easy reference.

```bash
# Import with automatic naming (uses filename)
stageflow process registry import my_process.yaml

# Import with custom name
stageflow process registry import external_process.yaml --name custom_name

# Short form with custom name
stageflow process registry import process.yaml -n my_workflow

```

**Example Output:**
```
✅ Process imported to registry as '@my_process'
```

After importing, you can reference the process using `@my_process` in other commands.

---

### 7. Process Registry Export

Copy a registry process to a file for sharing or backup.

```bash
# Export to file
stageflow process registry export user_onboarding exported_process.yaml

# Export with different format
stageflow process registry export customer_journey process.json

# JSON output
stageflow process registry export user_onboarding output.yaml --json
```

**Example Output:**
```
✅ Process '@user_onboarding' exported to exported_process.yaml
```

---

### 8. Process Registry Delete

Remove a process from the registry (with backup option).

```bash
# Delete with confirmation prompt
stageflow process registry delete old_process

# Force delete without confirmation
stageflow process registry delete old_process --force

# Short form
stageflow process registry delete old_process -f

# JSON output
stageflow process registry delete old_process --json
```

**Example Output:**
```
Are you sure you want to delete process 'old_process' from the registry? [y/N]: y
✅ Process 'old_process' deleted from registry
```

---

## Common Workflows

### 1. Create and Test a New Process

```bash
# Create new process
stageflow process new customer_journey.yaml

# View the structure
stageflow process view customer_journey.yaml

# Generate visualization
stageflow process diagram customer_journey.yaml

# Test with sample data
stageflow evaluate customer_journey.yaml -e test_data.json
```

### 2. Registry Management

```bash
# Import multiple processes
stageflow process registry import process1.yaml
stageflow process registry import process2.yaml

# List all registry processes
stageflow process registry list

# Use registry process
stageflow process view @process1
stageflow evaluate @process1 -e data.json

# Export for sharing
stageflow process registry export process1 shared_process.yaml
```

### 3. Validation and Debugging

```bash
# Check process validity
stageflow process view process.yaml

# Evaluate with verbose output
stageflow evaluate process.yaml -e data.json -v

# Test specific stage
stageflow evaluate process.yaml -e data.json -s stage_name
```

### 4. Automatic Stage Detection Workflow

When your process defines `stage_prop`, the element's data determines which stage to evaluate:

```bash
# Process configuration includes: stage_prop: "workflow.current_stage"

# Element 1: At draft stage
echo '{
  "workflow": {"current_stage": "draft"},
  "title": "My Document"
}' | stageflow evaluate process.yaml

# Element 2: At review stage
echo '{
  "workflow": {"current_stage": "review"},
  "title": "My Document",
  "reviewer": "jane@example.com"
}' | stageflow evaluate process.yaml

# Override auto-detection if needed
stageflow evaluate process.yaml -e element.json -s draft
```

**Process Example (process.yaml):**
```yaml
name: document_workflow
stage_prop: "workflow.current_stage"  # Enable auto-detection
initial_stage: draft
final_stage: published

stages:
  draft:
    name: "Draft"
    gates:
      - name: "to_review"
        target_stage: "review"
        locks: [...]
  review:
    name: "Review"
    gates: [...]
  published:
    name: "Published"
    is_final: true
```

---

## Global Options

All commands support:
- `--json`: Output results in JSON format for API integration
- `--help`: Display command-specific help

---

## Environment Variables

Configure StageFlow behavior using environment variables:

```bash
# Registry configuration
export STAGEFLOW_PROCESSES_DIR="./processes"      # Process files directory
export STAGEFLOW_DEFAULT_FORMAT="yaml"            # Default format: yaml|json
export STAGEFLOW_CREATE_DIR="true"                # Auto-create directory

# Backup settings
export STAGEFLOW_BACKUP_ENABLED="false"           # Enable backups
export STAGEFLOW_BACKUP_DIR="./backups"           # Backup directory
export STAGEFLOW_MAX_BACKUPS="5"                  # Max backup files

# Validation
export STAGEFLOW_STRICT_VALIDATION="true"         # Strict validation mode
```

---

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `process view` | Display process details | `stageflow process view process.yaml` |
| `evaluate` | Assess element against process | `stageflow evaluate process.yaml -e data.json` |
| `process new` | Create new process from template | `stageflow process new workflow.yaml` |
| `process diagram` | Generate visual diagram | `stageflow process diagram process.yaml` |
| `process registry list` | List registry processes | `stageflow process registry list` |
| `process registry import` | Add process to registry | `stageflow process registry import process.yaml` |
| `process registry export` | Export registry process | `stageflow process registry export name file.yaml` |
| `process registry delete` | Remove from registry | `stageflow process registry delete name` |

---

## Getting Help

```bash
# General help
stageflow --help

# Command group help
stageflow process --help
stageflow process registry --help

# Specific command help
stageflow process view --help
stageflow process new --help
stageflow process diagram --help
stageflow evaluate --help
```

---

## Examples Directory

StageFlow includes 25+ example process definitions demonstrating various patterns:

- **Simple workflows**: Basic 2-3 stage processes
- **Complex validation**: Multi-gate processes with advanced lock types
- **Real-world scenarios**: User onboarding, document approval, order fulfillment

Explore the `examples/` directory for complete working examples.
