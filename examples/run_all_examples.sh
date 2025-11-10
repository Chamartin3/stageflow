#!/bin/bash

# StageFlow Examples - Complete Test Suite Runner
# This script runs all example test cases to validate StageFlow functionality

set -o pipefail  # Ensure pipeline failures are caught

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

EXAMPLES_DIR="$(dirname "$0")"
OUTPUT_DIR="$EXAMPLES_DIR/test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "StageFlow Examples Test Suite - Started at $(date)"
echo "======================================================"

# Function to run command and capture output
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_result="$3"  # "pass" or "fail"

    echo "Running: $test_name"
    echo "Command: $command"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [[ "$expected_result" == "fail" ]]; then
        # Expected to fail
        if eval "$command" 2>&1 | tee "$OUTPUT_DIR/${test_name}_${TIMESTAMP}.log"; then
            echo "❌ UNEXPECTED PASS: $test_name (expected to fail)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        else
            echo "✅ EXPECTED FAIL: $test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        fi
    else
        # Expected to pass
        if eval "$command" 2>&1 | tee "$OUTPUT_DIR/${test_name}_${TIMESTAMP}.log"; then
            echo "✅ PASS: $test_name"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo "❌ FAIL: $test_name"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    fi
}

echo ""
echo "CASE 1: PROCESS CREATION AND VALIDATION"
echo "========================================"

echo ""
echo "1.1 Testing Valid Processes (should all pass):"
echo "------------------------------------------------"

run_test "valid_simple_2stage" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/valid_processes/simple_2stage.yaml" \
    "pass"

run_test "valid_complex_multistage" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/valid_processes/complex_multistage.yaml" \
    "pass"

run_test "valid_all_lock_types" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/valid_processes/all_lock_types.yaml" \
    "pass"

run_test "valid_multiple_gates" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/valid_processes/multiple_gates.yaml" \
    "pass"

echo ""
echo "1.2 Testing Invalid Structure (should all fail):"
echo "--------------------------------------------------"

run_test "invalid_missing_required" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/invalid_structure/missing_required.yaml" \
    "fail"

run_test "invalid_references" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/invalid_structure/invalid_references.yaml" \
    "fail"

run_test "invalid_malformed_syntax" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/invalid_structure/malformed_syntax.yaml" \
    "fail"

echo ""
echo "1.3 Testing Consistency Errors (should load with warnings):"
echo "------------------------------------------------------------"

run_test "consistency_circular_dependencies" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/consistency_errors/circular_dependencies.yaml" \
    "pass"

run_test "consistency_unreachable_stages" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/consistency_errors/unreachable_stages.yaml" \
    "pass"

run_test "consistency_missing_targets" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/consistency_errors/missing_targets.yaml" \
    "pass"

run_test "consistency_conflicting_gates" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/consistency_errors/conflicting_gates.yaml" \
    "pass"

run_test "consistency_invalid_locks" \
    "uv run stageflow process view $EXAMPLES_DIR/case1_process_creation/consistency_errors/invalid_locks.yaml" \
    "fail"

echo ""
echo "CASE 2: ELEMENT VALIDATION"
echo "==========================="

PROCESS_FILE="$EXAMPLES_DIR/case2_element_validation/normal_flow/process.yaml"

echo ""
echo "2.1 Testing Normal Flow - Ready Elements:"
echo "------------------------------------------"

run_test "element_ready_for_profile" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/ready_elements/user_ready_for_profile.json --stage registration" \
    "pass"

run_test "element_ready_for_verification" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/ready_elements/user_ready_for_verification.json --stage profile_setup" \
    "pass"

run_test "element_ready_for_activation" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/ready_elements/user_ready_for_activation.json --stage verification" \
    "pass"

echo ""
echo "2.2 Testing Normal Flow - Action Required:"
echo "-------------------------------------------"

run_test "element_missing_email_verification" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/action_required/user_missing_email_verification.json --stage registration" \
    "pass"

run_test "element_incomplete_profile" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/action_required/user_incomplete_profile.json --stage profile_setup" \
    "pass"

run_test "element_pending_identity_verification" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/action_required/user_pending_identity_verification.json --stage verification" \
    "pass"

echo ""
echo "2.3 Testing Normal Flow - Invalid Schema:"
echo "------------------------------------------"

run_test "element_invalid_email" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/invalid_schema/user_invalid_email.json --stage registration" \
    "pass"

run_test "element_missing_required_field" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/normal_flow/invalid_schema/user_missing_required_field.json --stage registration" \
    "pass"

echo ""
echo "2.4 Testing Regression Detection:"
echo "----------------------------------"

REGRESSION_PROCESS="$EXAMPLES_DIR/case2_element_validation/regression/process.yaml"

run_test "regression_to_basic" \
    "uv run stageflow evaluate $REGRESSION_PROCESS -e $EXAMPLES_DIR/case2_element_validation/regression/backward_regression/element_regressed_to_basic.json --stage basic" \
    "pass"

run_test "regression_to_intermediate" \
    "uv run stageflow evaluate $REGRESSION_PROCESS -e $EXAMPLES_DIR/case2_element_validation/regression/backward_regression/element_regressed_to_intermediate.json --stage intermediate" \
    "pass"

echo ""
echo "2.5 Testing Edge Cases:"
echo "------------------------"

run_test "edge_case_empty_element" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/edge_cases/empty_element.json --stage registration" \
    "pass"

run_test "edge_case_nested_properties" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/edge_cases/nested_properties.json --stage registration" \
    "pass"

run_test "edge_case_large_data" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/edge_cases/large_data.json --stage registration" \
    "pass"

run_test "edge_case_special_chars" \
    "uv run stageflow evaluate $PROCESS_FILE -e $EXAMPLES_DIR/case2_element_validation/edge_cases/special_chars.json --stage registration" \
    "pass"

echo ""
echo "CASE 3: PROCESS VISUALIZATION"
echo "=============================="

echo ""
echo "3.1 Testing Simple Visualizations:"
echo "-----------------------------------"

run_test "viz_linear_flow_mermaid" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/simple/linear_flow.yaml -o /tmp/linear_flow.md" \
    "pass"

run_test "viz_branching_flow_mermaid" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/simple/branching_flow.yaml -o /tmp/branching_flow.md" \
    "pass"

run_test "viz_linear_flow_graphviz" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/simple/linear_flow.yaml -o /tmp/linear_flow_gv.md" \
    "pass"

run_test "viz_branching_flow_graphviz" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/simple/branching_flow.yaml -o /tmp/branching_flow_gv.md" \
    "pass"

echo ""
echo "3.2 Testing Complex Visualizations:"
echo "------------------------------------"

run_test "viz_convergence_flow_mermaid" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/convergence_flow.yaml -o /tmp/convergence_flow.md" \
    "pass"

run_test "viz_parallel_paths_mermaid" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/parallel_paths.yaml -o /tmp/parallel_paths.md" \
    "pass"

run_test "viz_nested_conditions_mermaid" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/nested_conditions.yaml -o /tmp/nested_conditions.md" \
    "pass"

run_test "viz_convergence_flow_graphviz" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/convergence_flow.yaml -o /tmp/convergence_flow_gv.md" \
    "pass"

run_test "viz_parallel_paths_graphviz" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/parallel_paths.yaml -o /tmp/parallel_paths_gv.md" \
    "pass"

run_test "viz_nested_conditions_graphviz" \
    "uv run stageflow process diagram $EXAMPLES_DIR/case3_visualization/complex/nested_conditions.yaml -o /tmp/nested_conditions_gv.md" \
    "pass"

echo ""
echo "======================================================"
echo "StageFlow Examples Test Suite - Completed at $(date)"
echo ""
echo "Test results saved to: $OUTPUT_DIR"
echo ""
echo "Summary:"
echo "- Total tests: $TOTAL_TESTS"
echo "- Passed: $PASSED_TESTS"
echo "- Failed: $FAILED_TESTS"
echo ""
if [ $FAILED_TESTS -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed. Check logs for details."
    exit 1
fi