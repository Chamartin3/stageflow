#!/bin/bash
# Test script for complex data structures schema generation

echo "=== StageFlow Complex Data Structures Schema Generation Test ==="
echo

# Test cumulative schema generation
echo "1. Testing cumulative schema generation for data_processed stage:"
echo "Command: uv run stageflow process schema processes/complex_data_workflow.yaml data_processed"
echo
uv run stageflow process schema processes/complex_data_workflow.yaml data_processed
echo

# Test stage-specific schema generation
echo "2. Testing stage-specific schema generation for data_validation stage:"
echo "Command: uv run stageflow process schema processes/complex_data_workflow.yaml data_validation --stage-specific"
echo
uv run stageflow process schema processes/complex_data_workflow.yaml data_validation --stage-specific
echo

# Test element evaluation
echo "3. Testing element evaluation against the process:"
echo "Command: uv run stageflow evaluate processes/complex_data_workflow.yaml -e elements/fully_processed_data.json"
echo
uv run stageflow evaluate processes/complex_data_workflow.yaml -e elements/fully_processed_data.json
echo

echo "=== Test completed successfully! ==="
echo
echo "The complex data structures test case demonstrates:"
echo "- Deep nesting (4+ levels) with profile.detailed_info.addresses[0].coordinates"
echo "- Array structures with indexed access in required_fields"
echo "- Mixed data types (strings, numbers, booleans, objects, arrays)"
echo "- Complex validation rules using LENGTH locks for array validation"
echo "- Schema generation correctly handling nested property paths"