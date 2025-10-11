#!/bin/bash
# Default Schema Test - Test the new --default-schema functionality

set -e

echo "=== StageFlow Default Schema Test ==="
echo

# Set up temporary directory
TEMP_DIR=$(mktemp -d)
export STAGEFLOW_PROCESSES_DIR="$TEMP_DIR"
echo "Using temp directory: $TEMP_DIR"
echo

# Test 1: Create basic template process
echo "1. Creating basic template process:"
uv run stageflow manage --process basic_workflow --default-schema basic
echo

# Test 2: Create approval template process
echo "2. Creating approval template process:"
uv run stageflow manage --process content_review --default-schema approval
echo

# Test 3: Create onboarding template process
echo "3. Creating onboarding template process:"
uv run stageflow manage --process user_signup --default-schema onboarding
echo

# Test 4: List all created processes
echo "4. All created processes:"
uv run stageflow manage --list
echo

# Test 5: Show file contents
echo "5. Created files:"
ls -la "$TEMP_DIR"
echo

# Test 6: Show sample process content
echo "6. Sample basic workflow content:"
echo "---"
cat "$TEMP_DIR/basic_workflow.yaml" | head -20
echo "... (truncated)"
echo "---"
echo

echo "=== Default Schema Test Complete ==="
echo "Temp directory: $TEMP_DIR"
echo "Clean up with: rm -rf $TEMP_DIR"