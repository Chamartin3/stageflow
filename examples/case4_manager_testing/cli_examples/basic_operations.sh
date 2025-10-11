#!/bin/bash
# Basic CLI Operations Example
#
# This script demonstrates basic StageFlow manager CLI operations including
# listing, creating, editing, and synchronizing processes.

set -e  # Exit on any error

echo "=== StageFlow Manager Basic CLI Operations ==="
echo

# Set up temporary directory for this example
TEMP_DIR=$(mktemp -d)
export STAGEFLOW_PROCESSES_DIR="$TEMP_DIR"

echo "Using temporary processes directory: $TEMP_DIR"
echo

# 1. List processes (should be empty initially)
echo "1. Listing processes (initially empty):"
uv run stageflow manage --list || echo "  No processes found (expected)"
echo

# 2. Create a simple process
echo "2. Creating a simple workflow process:"
SIMPLE_PROCESS='{
    "name": "simple_workflow",
    "description": "A basic two-stage workflow",
    "stages": {
        "start": {
            "name": "Start Stage",
            "description": "Initial stage",
            "schema": {
                "required_fields": ["id"]
            },
            "gates": [{
                "name": "proceed",
                "description": "Proceed to end",
                "target_stage": "end",
                "locks": [{"exists": "id"}]
            }]
        },
        "end": {
            "name": "End Stage",
            "description": "Final stage",
            "schema": {
                "required_fields": []
            },
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "start",
    "final_stage": "end"
}'

uv run stageflow manage --process simple_workflow --create "$SIMPLE_PROCESS"
echo

# 3. List processes again (should show the created process)
echo "3. Listing processes after creation:"
uv run stageflow manage --list
echo

# 4. Create a user onboarding process
echo "4. Creating a user onboarding process:"
USER_PROCESS='{
    "name": "user_onboarding",
    "description": "User onboarding workflow",
    "stages": {
        "email_signup": {
            "name": "Email Signup",
            "description": "User provides email",
            "schema": {
                "required_fields": ["email", "meta.email_verified_at"]
            },
            "gates": [{
                "name": "email_verified",
                "description": "Email verification completed",
                "target_stage": "profile_setup",
                "locks": [
                    {"exists": "email"},
                    {"exists": "meta.email_verified_at"}
                ]
            }]
        },
        "profile_setup": {
            "name": "Profile Setup",
            "description": "User completes profile",
            "schema": {
                "required_fields": ["profile.first_name", "profile.last_name"]
            },
            "gates": [{
                "name": "profile_complete",
                "description": "Profile is complete",
                "target_stage": "active_user",
                "locks": [
                    {"exists": "profile.first_name"},
                    {"exists": "profile.last_name"}
                ]
            }]
        },
        "active_user": {
            "name": "Active User",
            "description": "User account is active",
            "schema": {
                "required_fields": []
            },
            "gates": [],
            "is_final": true
        }
    },
    "initial_stage": "email_signup",
    "final_stage": "active_user"
}'

uv run stageflow manage --process user_onboarding --create "$USER_PROCESS"
echo

# 5. Add a new stage to the user onboarding process
echo "5. Adding verification stage to user onboarding:"
VERIFICATION_STAGE='{
    "name": "verification",
    "description": "Identity verification process",
    "schema": {
        "required_fields": ["verification.document_uploaded", "verification.status"]
    },
    "gates": [{
        "name": "verification_approved",
        "description": "Verification approved",
        "target_stage": "active_user",
        "locks": [
            {"type": "equals", "property_path": "verification.document_uploaded", "expected_value": true},
            {"type": "equals", "property_path": "verification.status", "expected_value": "approved"}
        ]
    }]
}'

uv run stageflow manage --process user_onboarding --add-stage "$VERIFICATION_STAGE"
echo

# 6. Update the profile_setup stage to go to verification instead
echo "6. Note: To redirect profile_setup to verification, you would need to edit the process file manually"
echo "   or use additional CLI operations (this is an advanced workflow)"
echo

# 7. Sync the changes
echo "7. Syncing changes to user_onboarding process:"
uv run stageflow manage --process user_onboarding --sync
echo

# 8. List all processes
echo "8. Final process list:"
uv run stageflow manage --list
echo

# 9. Show what files were created
echo "9. Created files:"
ls -la "$TEMP_DIR"
echo

# 10. Show content of one process file
echo "10. Content of simple_workflow.yaml:"
echo "---"
cat "$TEMP_DIR/simple_workflow.yaml"
echo "---"
echo

# 11. Test sync-all operation
echo "11. Testing sync-all operation:"
uv run stageflow manage --sync-all
echo

echo "=== Basic CLI Operations Complete ==="
echo "Temporary directory: $TEMP_DIR"
echo "You can explore the created files or clean up with: rm -rf $TEMP_DIR"