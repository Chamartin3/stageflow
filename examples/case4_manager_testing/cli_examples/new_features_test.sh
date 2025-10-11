#!/bin/bash
# Test new manager features: --create-default and --edit

set -e

echo "=== Testing New Manager Features ==="
echo

# Set up temporary directory
TEMP_DIR=$(mktemp -d)
export STAGEFLOW_PROCESSES_DIR="$TEMP_DIR"
echo "Using temp directory: $TEMP_DIR"
echo

# Test 1: Create process with default schema using --create-default
echo "1. Testing --create-default flag:"
uv run stageflow manage --process test_default --create-default
echo

# Test 2: List processes to verify creation
echo "2. Listing processes:"
uv run stageflow manage --list
echo

# Test 3: Show created file
echo "3. Created files:"
ls -la "$TEMP_DIR"
echo

# Test 4: Show content of the created process
echo "4. Content of created process:"
echo "---"
head -15 "$TEMP_DIR/test_default.yaml"
echo "... (truncated)"
echo "---"
echo

# Test 5: Test --edit flag (this would normally open an editor)
# For testing purposes, we'll just test that it finds the right editor
echo "5. Testing --edit flag detection (would normally open editor):"
echo "Available editors:"
which nano 2>/dev/null && echo "  nano: available" || echo "  nano: not found"
which vim 2>/dev/null && echo "  vim: available" || echo "  vim: not found"
which vi 2>/dev/null && echo "  vi: available" || echo "  vi: not found"
echo

# Test 6: Test editor selection (we can't actually open editor in script)
echo "6. Editor selection test (displaying what would happen):"
if [ -n "$EDITOR" ]; then
    echo "  Would use EDITOR environment variable: $EDITOR"
else
    echo "  Would use fallback editor detection"
fi
echo

# Test 7: Test validation - create-default without process name
echo "7. Testing validation (should fail):"
set +e
uv run stageflow manage --create-default 2>&1 | head -1
set -e
echo

# Test 8: Test validation - edit without process name
echo "8. Testing edit validation (should fail):"
set +e
uv run stageflow manage --edit 2>&1 | head -1
set -e
echo

echo "=== New Features Test Complete ==="
echo "Temp directory: $TEMP_DIR"
echo "Clean up with: rm -rf $TEMP_DIR"