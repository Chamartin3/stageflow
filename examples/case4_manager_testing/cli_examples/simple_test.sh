#!/bin/bash
# Simple Manager Test - Demonstrates core StageFlow manager functionality

set -e

echo "=== StageFlow Manager Simple Test ==="
echo

# Set up temporary directory
TEMP_DIR=$(mktemp -d)
export STAGEFLOW_PROCESSES_DIR="$TEMP_DIR"
echo "Using temp directory: $TEMP_DIR"
echo

# 1. List processes (initially empty)
echo "1. Initial process list (should be empty):"
set +e  # Allow errors for this command
uv run stageflow manage --list 2>/dev/null || echo "  No processes (expected)"
set -e  # Resume error checking
echo

# 2. Create a simple two-stage process
echo "2. Creating simple process:"
SIMPLE_PROCESS='{
    "name": "test_workflow",
    "description": "Simple test workflow",
    "stages": {
        "start": {
            "name": "Start",
            "schema": {"required_fields": ["id"]},
            "gates": [{
                "name": "to_end",
                "target_stage": "end",
                "locks": [{"exists": "id"}]
            }]
        },
        "end": {
            "name": "End",
            "schema": {"required_fields": []},
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "start",
    "final_stage": "end"
}'

uv run stageflow manage --process test_workflow --create "$SIMPLE_PROCESS"
echo

# 3. List processes again
echo "3. Process list after creation:"
uv run stageflow manage --list
echo

# 4. Add a middle stage
echo "4. Adding middle stage:"
MIDDLE_STAGE='{
    "name": "middle",
    "description": "Middle stage",
    "schema": {"required_fields": ["data"]},
    "gates": [{
        "name": "to_end",
        "target_stage": "end",
        "locks": [{"exists": "data"}]
    }]
}'

uv run stageflow manage --process test_workflow --add-stage "$MIDDLE_STAGE"
echo

# 5. Sync the process
echo "5. Syncing process:"
uv run stageflow manage --process test_workflow --sync
echo

# 6. Show final process list
echo "6. Final process list:"
uv run stageflow manage --list
echo

# 7. Show created files
echo "7. Created files:"
ls -la "$TEMP_DIR"
echo

echo "=== Manager Test Complete ==="
echo "Temp directory: $TEMP_DIR"
echo "Clean up with: rm -rf $TEMP_DIR"