#!/bin/bash
# Advanced CLI Workflows Example
#
# This script demonstrates advanced StageFlow manager CLI workflows including
# complex process creation, batch operations, error handling, and process management patterns.

set -e  # Exit on any error

echo "=== StageFlow Manager Advanced CLI Workflows ==="
echo

# Set up temporary directory for this example
TEMP_DIR=$(mktemp -d)
export STAGEFLOW_PROCESSES_DIR="$TEMP_DIR"

echo "Using temporary processes directory: $TEMP_DIR"
echo

# Enable backup functionality
export STAGEFLOW_BACKUP_ENABLED="true"
export STAGEFLOW_BACKUP_DIR="$TEMP_DIR/.backups"
export STAGEFLOW_MAX_BACKUPS="10"

echo "Backup configuration:"
echo "  STAGEFLOW_BACKUP_ENABLED=$STAGEFLOW_BACKUP_ENABLED"
echo "  STAGEFLOW_BACKUP_DIR=$STAGEFLOW_BACKUP_DIR"
echo

# 1. Create multiple processes in batch
echo "1. Creating multiple processes for different domains:"

# E-commerce order process
ECOMMERCE_PROCESS='{
    "name": "ecommerce_order",
    "description": "E-commerce order processing",
    "stages": {
        "cart": {
            "name": "Shopping Cart",
            "gates": [{
                "name": "checkout",
                "target_stage": "payment",
                "locks": [
                    {"exists": "cart_id"},
                    {"exists": "items"},
                    {"greater_than": {"property_path": "items", "expected_value": []}}
                ]
            }]
        },
        "payment": {
            "name": "Payment Processing",
            "gates": [{
                "name": "payment_success",
                "target_stage": "confirmed",
                "locks": [
                    {"equals": {"property_path": "payment_status", "expected_value": "completed"}}
                ]
            }]
        },
        "confirmed": {
            "name": "Order Confirmed",
            "gates": [{
                "name": "ship_order",
                "target_stage": "shipped",
                "locks": [{"exists": "confirmed_at"}]
            }]
        },
        "shipped": {
            "name": "Order Shipped",
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "cart",
    "final_stage": "shipped"
}'

# Content approval process
CONTENT_PROCESS='{
    "name": "content_approval",
    "description": "Content review and approval",
    "stages": {
        "draft": {
            "name": "Draft",
            "gates": [{
                "name": "submit_review",
                "target_stage": "review",
                "locks": [
                    {"exists": "title"},
                    {"exists": "content"},
                    {"exists": "author"}
                ]
            }]
        },
        "review": {
            "name": "Under Review",
            "gates": [
                {
                    "name": "approve",
                    "target_stage": "published",
                    "locks": [
                        {"equals": {"property_path": "review.status", "expected_value": "approved"}}
                    ]
                },
                {
                    "name": "reject",
                    "target_stage": "draft",
                    "locks": [
                        {"equals": {"property_path": "review.status", "expected_value": "rejected"}}
                    ]
                }
            ]
        },
        "published": {
            "name": "Published",
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "draft",
    "final_stage": "published"
}'

# Data pipeline process
PIPELINE_PROCESS='{
    "name": "data_pipeline",
    "description": "Data processing pipeline",
    "stages": {
        "ingestion": {
            "name": "Data Ingestion",
            "gates": [{
                "name": "validate_data",
                "target_stage": "processing",
                "locks": [
                    {"exists": "data_source"},
                    {"exists": "raw_data"},
                    {"greater_than": {"property_path": "quality_score", "expected_value": 0.8}}
                ]
            }]
        },
        "processing": {
            "name": "Data Processing",
            "gates": [{
                "name": "processing_complete",
                "target_stage": "output",
                "locks": [
                    {"exists": "processed_data"},
                    {"exists": "processing_stats"}
                ]
            }]
        },
        "output": {
            "name": "Data Output",
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "ingestion",
    "final_stage": "output"
}'

# Create all processes
echo "Creating ecommerce_order process..."
uv run stageflow manage --process ecommerce_order --create "$ECOMMERCE_PROCESS"

echo "Creating content_approval process..."
uv run stageflow manage --process content_approval --create "$CONTENT_PROCESS"

echo "Creating data_pipeline process..."
uv run stageflow manage --process data_pipeline --create "$PIPELINE_PROCESS"

echo

# 2. List all processes
echo "2. Current processes:"
uv run stageflow manage --list
echo

# 3. Demonstrate error handling - try to create duplicate
echo "3. Testing error handling (trying to create duplicate):"
set +e  # Allow errors for this section
uv run stageflow manage --process ecommerce_order --create "$ECOMMERCE_PROCESS"
echo "Expected error above - process already exists"
set -e  # Resume error checking
echo

# 4. Add stages to multiple processes
echo "4. Adding additional stages to processes:"

# Add quality assurance stage to content approval
QA_STAGE='{
    "name": "qa_review",
    "description": "Quality assurance review",
    "gates": [{
        "name": "qa_approved",
        "target_stage": "published",
        "locks": [
            {"equals": {"property_path": "qa.status", "expected_value": "passed"}},
            {"exists": "qa.reviewer"}
        ]
    }]
}'

echo "Adding QA stage to content_approval..."
uv run stageflow manage --process content_approval --add-stage "$QA_STAGE"

# Add monitoring stage to data pipeline
MONITORING_STAGE='{
    "name": "monitoring",
    "description": "Data quality monitoring",
    "gates": [{
        "name": "monitoring_setup",
        "target_stage": "output",
        "locks": [
            {"exists": "monitoring_config"},
            {"equals": {"property_path": "monitoring.enabled", "expected_value": true}}
        ]
    }]
}'

echo "Adding monitoring stage to data_pipeline..."
uv run stageflow manage --process data_pipeline --add-stage "$MONITORING_STAGE"

echo

# 5. Batch sync all changes
echo "5. Syncing all modified processes:"
uv run stageflow manage --sync-all
echo

# 6. Show backup functionality
echo "6. Checking backup functionality:"
if [ -d "$STAGEFLOW_BACKUP_DIR" ]; then
    echo "Backup directory contents:"
    ls -la "$STAGEFLOW_BACKUP_DIR"
else
    echo "Backup directory not created (backups may not be working)"
fi
echo

# 7. Process validation example
echo "7. Testing process management with validation:"

# Try to remove a critical stage (should work but may cause consistency issues)
echo "Removing 'payment' stage from ecommerce_order (this may cause issues):"
set +e
uv run stageflow manage --process ecommerce_order --remove-stage payment
if [ $? -eq 0 ]; then
    echo "Stage removed successfully"
else
    echo "Stage removal failed (expected due to consistency checks)"
fi
set -e
echo

# 8. Configuration demonstration
echo "8. Environment configuration in use:"
echo "  Processes directory: $STAGEFLOW_PROCESSES_DIR"
echo "  Backup enabled: $STAGEFLOW_BACKUP_ENABLED"
echo "  Backup directory: $STAGEFLOW_BACKUP_DIR"
echo "  Max backups: $STAGEFLOW_MAX_BACKUPS"
echo

# 9. Process file analysis
echo "9. Process file analysis:"
echo "Created process files:"
for file in "$TEMP_DIR"/*.yaml; do
    if [ -f "$file" ]; then
        echo "  $(basename "$file"): $(wc -l < "$file") lines"
    fi
done
echo

# 10. Advanced operations with different formats
echo "10. Testing JSON format support:"
export STAGEFLOW_DEFAULT_FORMAT="json"

SIMPLE_JSON_PROCESS='{
    "name": "json_test",
    "stages": {
        "start": {
            "name": "Start",
            "gates": [{
                "name": "to_end",
                "target_stage": "end",
                "locks": [{"exists": "id"}]
            }]
        },
        "end": {
            "name": "End",
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "start",
    "final_stage": "end"
}'

uv run stageflow manage --process json_test --create "$SIMPLE_JSON_PROCESS"

# Check what format was used
echo "Files after JSON format test:"
ls -la "$TEMP_DIR"
echo

# Reset to YAML format
export STAGEFLOW_DEFAULT_FORMAT="yaml"

# 11. Final process inventory
echo "11. Final process inventory:"
uv run stageflow manage --list
echo

# 12. Sample process content
echo "12. Sample process content (content_approval.yaml):"
if [ -f "$TEMP_DIR/content_approval.yaml" ]; then
    echo "---"
    head -20 "$TEMP_DIR/content_approval.yaml"
    echo "... (truncated)"
    echo "---"
fi
echo

echo "=== Advanced CLI Workflows Complete ==="
echo
echo "Summary of what was accomplished:"
echo "- Created multiple complex processes across different domains"
echo "- Demonstrated error handling and validation"
echo "- Added stages to existing processes"
echo "- Used batch sync operations"
echo "- Tested backup functionality"
echo "- Explored different file formats (YAML/JSON)"
echo "- Managed multiple processes with different configurations"
echo
echo "Temporary directory: $TEMP_DIR"
echo "Explore the files or clean up with: rm -rf $TEMP_DIR"