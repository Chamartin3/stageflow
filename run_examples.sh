#!/bin/bash

# StageFlow Examples Runner
# Interactive test runner with selectable individual tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Global options
VERBOSE=false
JSON_OUTPUT=false

# Check if glow is available
if ! command -v glow &> /dev/null; then
    echo -e "${YELLOW}Warning: glow not found. Install with: brew install glow or go install github.com/charmbracelet/glow@latest${NC}"
    USE_GLOW=false
else
    USE_GLOW=true
fi

# Function to display help
show_help() {
    cat << EOF
StageFlow Examples Runner

Usage: $0 [options]

Options:
    -h, --help          Show this help message
    -a, --all           Run all test categories
    -v, --verbose       Run with verbose output
    --json              Use JSON output format

Interactive Mode:
    Run without arguments to see selectable test categories
EOF
}

# Function to collect all available tests
collect_tests() {
    local tests=()

    # Process validation tests
    while IFS= read -r -d '' file; do
        local basename=$(basename "$file" .yaml)
        local category="Process Validation"
        local description="Test process creation and validation"
        local expected="✅ Valid process with stage descriptions and possible transitions"
        tests+=("$category|$basename|$description|$expected|process|$file")
    done < <(find examples/case1_process_creation/valid_processes -name "*.yaml" -print0 2>/dev/null)

    # Consistency error tests
    while IFS= read -r -d '' file; do
        local basename=$(basename "$file" .yaml)
        local category="Consistency Errors"
        local description="Test consistency error detection"
        local expected="❌ Invalid process with detailed consistency issues listed"
        tests+=("$category|$basename|$description|$expected|consistency|$file")
    done < <(find examples/case1_process_creation/consistency_errors -name "*.yaml" -print0 2>/dev/null)

    # Element evaluation tests
    local test_element="/tmp/content_element.json"
    cat > "$test_element" << 'EOF'
{
    "content": {"text": "Hello world", "word_count": 2},
    "author": {"trusted_status": false},
    "flags": {"spam_detected": false}
}
EOF

    # Use first valid process for element evaluation
    if find examples/case1_process_creation/valid_processes -name "*.yaml" | head -1 | read -r process_file; then
        tests+=("Element Evaluation|Basic Element Test|Test element evaluation against process|📋 Process info with stages, then element status with feedback|element|$process_file|$test_element")
        tests+=("Element Evaluation|Element with Stage|Test element evaluation at specific stage|📋 Process info with stages, then stage-specific validation results|element_stage|$process_file|$test_element|start")
    fi

    # Default properties examples - demonstrating concept
    local defaults_demo_process="examples/case2_element_validation/default_properties/defaults_demo_process.yaml"
    if [ -f "$defaults_demo_process" ]; then
        tests+=("Default Properties Concept|User Needs Defaults|Element missing configuration that should get defaults|⚠️ Action required listing missing properties (ideally would suggest defaults)|element_stage|$defaults_demo_process|examples/case2_element_validation/default_properties/user_needs_defaults.json|needs_configuration")
        tests+=("Default Properties Concept|User With Defaults|Element with defaults already applied|✅ Ready to advance with all required configuration present|element_stage|$defaults_demo_process|examples/case2_element_validation/default_properties/user_with_applied_defaults.json|needs_configuration")
        tests+=("Default Properties Concept|Minimal User Ready|Element ready to progress from minimal data stage|✅ Ready to advance to configuration stage|element_stage|$defaults_demo_process|examples/case2_element_validation/default_properties/minimal_user.json|minimal_data")
    fi

    # Original default properties examples
    local defaults_process="examples/case2_element_validation/default_properties/process.yaml"
    if [ -f "$defaults_process" ]; then
        tests+=("Default Properties|Profile Ready|Element ready to advance with basic profile complete|✅ Ready for transition to preferences_config stage|element_stage|$defaults_process|examples/case2_element_validation/default_properties/profile_needs_defaults.json|profile_setup")
        tests+=("Default Properties|With Applied Defaults|Element with defaults already applied|✅ Shows configuration with applied default values|element_stage|$defaults_process|examples/case2_element_validation/default_properties/profile_with_applied_defaults.json|profile_setup")
    fi

    # Visualization tests
    while IFS= read -r -d '' file; do
        local basename=$(basename "$file" .yaml)
        local category="Visualization"
        local description="Generate Mermaid diagram"
        local expected="✅ Valid Mermaid markdown file created with process flowchart"
        tests+=("$category|$basename Diagram|$description|$expected|visualization|$file")
    done < <(find examples/case1_process_creation/valid_processes -name "*.yaml" -print0 2>/dev/null | head -3)

    # CLI demonstration tests
    if find examples/case1_process_creation/valid_processes -name "*.yaml" | head -1 | read -r process_file; then
        tests+=("CLI Demo|Help Command|Show CLI help|📖 Complete CLI usage documentation and available options|cli_help|")
        tests+=("CLI Demo|Verbose Output|Test verbose mode|📝 Detailed output with progress indicators and extra information|cli_verbose|$process_file")
        tests+=("CLI Demo|JSON Output|Test JSON response format|📋 Structured JSON response suitable for API integration|cli_json|$process_file")
    fi

    printf '%s\n' "${tests[@]}"
}

# Function to create test selection markdown for glow
create_test_selection_markdown() {
    local counter=1
    echo "# StageFlow Test Selection"
    echo ""
    echo "Choose individual tests to run:"
    echo ""

    collect_tests | while IFS='|' read -r category name description expected type file extra stage; do
        echo "## $counter. [$category] $name"
        echo "**Description**: $description"
        echo "**Expected Result**: $expected"
        echo "**Type**: $type"
        if [ -n "$file" ]; then
            echo "**File**: $(basename "$file")"
        fi
        echo ""
        ((counter++))
    done

    echo "---"
    echo "**Commands**: Enter test number, 'all' for all tests, or 'q' to quit"
}

# Function to run individual test
run_individual_test() {
    local test_data="$1"
    IFS='|' read -r category name description expected type file extra stage <<< "$test_data"

    echo -e "${BLUE}=== Running [$category] $name ===${NC}"
    echo -e "Description: $description"
    echo -e "${YELLOW}Expected Result: $expected${NC}"
    echo

    # Build command arguments
    local cmd_args=()
    if [ "$JSON_OUTPUT" = true ]; then
        cmd_args+=("--json")
    fi
    if [ "$VERBOSE" = true ]; then
        cmd_args+=("--verbose")
    fi

    case "$type" in
        "process")
            echo "Testing process: $(basename "$file")"
            uv run stageflow -p "$file" "${cmd_args[@]}" || true
            ;;
        "consistency")
            echo "Testing consistency: $(basename "$file")"
            uv run stageflow -p "$file" "${cmd_args[@]}" || true
            ;;
        "element")
            echo "Testing element evaluation: $(basename "$file")"
            uv run stageflow -p "$file" -e "$extra" "${cmd_args[@]}" || true
            ;;
        "element_stage")
            echo "Testing element evaluation at stage '$stage': $(basename "$file")"
            uv run stageflow -p "$file" -e "$extra" -s "$stage" "${cmd_args[@]}" || true
            ;;
        "visualization")
            local output_file="test_diagram_$(basename "$file" .yaml).md"
            echo "Generating visualization: $output_file"
            uv run stageflow -p "$file" --view -o "$output_file" "${cmd_args[@]}" || true
            ;;
        "cli_help")
            echo "Showing CLI help:"
            uv run stageflow --help
            ;;
        "cli_verbose")
            echo "Testing verbose mode: $(basename "$file")"
            uv run stageflow -p "$file" --verbose
            ;;
        "cli_json")
            echo "Testing JSON output: $(basename "$file")"
            uv run stageflow -p "$file" --json
            ;;
        *)
            echo -e "${RED}Unknown test type: $type${NC}"
            return 1
            ;;
    esac
    echo
}

# Function to run all tests
run_all_tests() {
    echo -e "${YELLOW}=== Running All Tests ===${NC}"
    local test_count=0

    collect_tests | while IFS='|' read -r category name description expected type file extra stage; do
        ((test_count++))
        echo -e "${GREEN}[$test_count] Running: [$category] $name${NC}"
        run_individual_test "$category|$name|$description|$expected|$type|$file|$extra|$stage"
    done
}

# Function to show interactive menu
show_interactive_menu() {
    # Collect all tests into an array
    local tests_array=()
    while IFS= read -r line; do
        tests_array+=("$line")
    done < <(collect_tests)

    if [ "$USE_GLOW" = true ]; then
        # Create temporary markdown file
        local temp_md=$(mktemp)
        create_test_selection_markdown > "$temp_md"

        # Show with glow
        echo -e "${BLUE}StageFlow Test Selection${NC}"
        echo -e "${YELLOW}Displaying test options with glow...${NC}"
        echo
        glow "$temp_md"
        rm "$temp_md"
    else
        # Fallback to simple text display
        echo "StageFlow Test Selection"
        echo "========================"
        echo
        local counter=1
        for test_data in "${tests_array[@]}"; do
            IFS='|' read -r category name description expected type file extra stage <<< "$test_data"
            echo "$counter) [$category] $name"
            echo "   Description: $description"
            echo -e "   Expected: ${YELLOW}$expected${NC}"
            if [ -n "$file" ]; then
                echo "   File: $(basename "$file")"
            fi
            echo
            ((counter++))
        done
    fi

    echo
    echo -e "${GREEN}Available commands:${NC}"
    echo "  • Enter test number (1-${#tests_array[@]}) to run individual test"
    echo "  • Enter 'all' to run all tests"
    echo "  • Enter 'q' to quit"
    echo
    read -p "Your choice: " choice

    case $choice in
        [0-9]*)
            if [ "$choice" -ge 1 ] && [ "$choice" -le "${#tests_array[@]}" ]; then
                local selected_test="${tests_array[$((choice-1))]}"
                run_individual_test "$selected_test"
                echo
                echo -e "${GREEN}Test completed. Press Enter to continue...${NC}"
                read
                show_interactive_menu
            else
                echo -e "${RED}Invalid test number. Please try again.${NC}"
                sleep 2
                show_interactive_menu
            fi
            ;;
        "all"|"ALL")
            run_all_tests
            ;;
        "q"|"Q"|"quit"|"exit")
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            sleep 2
            show_interactive_menu
            ;;
    esac
}

# Parse command line arguments
RUN_ALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
echo -e "${GREEN}StageFlow Examples Runner${NC}"
echo "========================="
echo

# Check if uv and stageflow are available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv not found. Please install uv package manager.${NC}"
    exit 1
fi

# Test if stageflow is available
if ! uv run stageflow --help &> /dev/null; then
    echo -e "${RED}Error: stageflow not available. Run 'uv sync' first.${NC}"
    exit 1
fi

if [ "$RUN_ALL" = true ]; then
    run_all_tests
else
    show_interactive_menu
fi

echo -e "${GREEN}Examples run completed!${NC}"