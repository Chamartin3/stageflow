"""Practical usage tests for schema functionality.

These tests demonstrate real-world scenarios where get_schema()
provides value to developers and users.
"""

import pytest

from stageflow import DictElement
from stageflow.lock import LockType
from stageflow.models import ProcessDefinition
from stageflow.process import Process


class TestSchemaPracticalUsage:
    """Tests demonstrating practical schema usage patterns."""

    @pytest.fixture
    def user_onboarding_process(self) -> Process:
        """Create a realistic user onboarding process with schemas."""
        config: ProcessDefinition = {
            "name": "user_onboarding",
            "description": "Multi-stage user onboarding process",
            "initial_stage": "registration",
            "final_stage": "active",
            "stages": {
                "registration": {
                    "name": "Registration",
                    "description": "User registration stage",
                    "expected_properties": {
                        "email": {"type": "str", "default": None},
                        "password": {"type": "str", "default": None},
                    },
                    "gates": [
                        {
                            "name": "to_verification",
                            "description": "Move to email verification",
                            "target_stage": "verification",
                            "parent_stage": "registration",
                            "locks": [
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "email",
                                    "expected_value": None,
                                },
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "password",
                                    "expected_value": None,
                                },
                            ],
                        }
                    ],
                    "expected_actions": [],
                    "is_final": False,
                },
                "verification": {
                    "name": "Email Verification",
                    "description": "Email verification stage",
                    "expected_properties": {
                        "verification_token": {"type": "str", "default": None},
                        "verified_at": {"type": "str", "default": None},
                    },
                    "gates": [
                        {
                            "name": "to_profile",
                            "description": "Move to profile setup",
                            "target_stage": "profile_setup",
                            "parent_stage": "verification",
                            "locks": [
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "verified_at",
                                    "expected_value": None,
                                }
                            ],
                        }
                    ],
                    "expected_actions": [],
                    "is_final": False,
                },
                "profile_setup": {
                    "name": "Profile Setup",
                    "description": "User profile setup stage",
                    "expected_properties": {
                        "profile": {
                            "first_name": {"type": "str", "default": None},
                            "last_name": {"type": "str", "default": None},
                            "age": {"type": "int", "default": 18},
                        }
                    },
                    "gates": [
                        {
                            "name": "to_active",
                            "description": "Activate user account",
                            "target_stage": "active",
                            "parent_stage": "profile_setup",
                            "locks": [
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "profile.first_name",
                                    "expected_value": None,
                                },
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "profile.last_name",
                                    "expected_value": None,
                                },
                            ],
                        }
                    ],
                    "expected_actions": [],
                    "is_final": False,
                },
                "active": {
                    "name": "Active User",
                    "description": "Fully activated user",
                    "expected_properties": {},
                    "gates": [],
                    "expected_actions": [],
                    "is_final": True,
                },
            },
        }
        return Process(config)

    def test_schema_guides_element_creation(self, user_onboarding_process):
        """Demonstrate using schema to guide element creation.

        Scenario: Developer wants to create an element that will
        pass validation for a specific stage.
        """
        # Get schema for registration stage to understand requirements
        registration_schema = user_onboarding_process.get_schema(
            "registration", partial=True
        )

        # Verify schema tells us what properties are needed
        assert "email" in registration_schema
        assert "password" in registration_schema
        assert registration_schema["email"]["type"] == "str"
        assert registration_schema["password"]["type"] == "str"

        # Create element based on schema
        element_data = {}
        for prop_path, prop_def in registration_schema.items():
            if prop_def and prop_def.get("default") is not None:
                element_data[prop_path] = prop_def["default"]
            else:
                # Provide a value for required properties
                if prop_path == "email":
                    element_data[prop_path] = "user@example.com"
                elif prop_path == "password":
                    element_data[prop_path] = "secure_password"

        element = DictElement(element_data)

        # Verify element validates successfully
        result = user_onboarding_process.evaluate(element, "registration")
        assert result["stage_result"].status != "incomplete"

    def test_schema_identifies_missing_properties_before_evaluation(
        self, user_onboarding_process
    ):
        """Demonstrate using schema to identify issues before evaluation.

        Scenario: User wants to know what properties are missing
        before attempting evaluation.
        """
        # Create incomplete element
        incomplete_element = DictElement(
            {"email": "user@example.com"}
        )  # Missing password

        # Get schema for target stage
        schema = user_onboarding_process.get_schema("registration", partial=True)

        # Compare with element properties to identify missing ones
        missing_properties = []
        for prop_path in schema.keys():
            if not incomplete_element.has_property(prop_path):
                missing_properties.append(prop_path)

        # Verify we can detect missing properties before evaluation
        assert "password" in missing_properties
        assert len(missing_properties) == 1

        # This pre-check allows providing helpful messages to users
        # before expensive evaluation operations

    def test_schema_helps_debug_validation_failures(self, user_onboarding_process):
        """Demonstrate using schema to debug why validation failed.

        Scenario: Element fails validation and user wants to understand
        what properties were expected.
        """
        # Element fails validation
        failing_element = DictElement({"email": "user@example.com"})
        result = user_onboarding_process.evaluate(failing_element, "registration")

        # Evaluation fails with INVALID_SCHEMA
        assert result["stage_result"].status == "incomplete"

        # Get schema to see what was expected
        expected_schema = user_onboarding_process.get_schema(
            "registration", partial=True
        )

        # Compare with actual element to generate diagnostic message
        diagnostic_messages = []
        for prop_path, prop_def in expected_schema.items():
            if not failing_element.has_property(prop_path):
                prop_type = prop_def["type"] if prop_def else "unknown"
                diagnostic_messages.append(
                    f"Missing property: '{prop_path}' (expected type: {prop_type})"
                )

        # Verify we can generate helpful diagnostic messages
        assert len(diagnostic_messages) == 1
        assert "password" in diagnostic_messages[0]
        assert "str" in diagnostic_messages[0]

    def test_cumulative_schema_shows_full_journey(self, user_onboarding_process):
        """Demonstrate cumulative schema showing complete requirements.

        Scenario: User wants to understand all properties needed to
        reach a specific stage from initial stage.
        """
        # Get cumulative schema for profile_setup stage
        cumulative_schema = user_onboarding_process.get_schema(
            "profile_setup", partial=False
        )

        # Should include properties from all previous stages
        # From registration stage
        assert "email" in cumulative_schema
        assert "password" in cumulative_schema

        # From verification stage
        assert "verification_token" in cumulative_schema
        assert "verified_at" in cumulative_schema

        # From profile_setup stage (nested structure)
        assert "profile" in cumulative_schema
        assert isinstance(cumulative_schema["profile"], dict)
        assert "first_name" in cumulative_schema["profile"]
        assert "last_name" in cumulative_schema["profile"]
        assert "age" in cumulative_schema["profile"]

        # This helps users understand the complete data journey
        # Top-level properties: email, password, verification_token, verified_at, profile
        assert len(cumulative_schema) == 5

    def test_schema_comparison_between_stages(self, user_onboarding_process):
        """Demonstrate comparing schemas between stages.

        Scenario: User wants to understand what new properties
        are required when moving between stages.
        """
        # Get schema for current stage (registration)
        registration_schema = user_onboarding_process.get_schema(
            "registration", partial=True
        )

        # Get schema for next stage (verification)
        verification_schema = user_onboarding_process.get_schema(
            "verification", partial=True
        )

        # Identify new properties in verification stage
        new_properties = set(verification_schema.keys()) - set(
            registration_schema.keys()
        )

        # Verify we can identify the delta
        assert "verification_token" in new_properties
        assert "verified_at" in new_properties
        assert len(new_properties) == 2

        # This helps users understand what data they need to add
        # when transitioning between stages

    def test_schema_generation_for_documentation(self, user_onboarding_process):
        """Demonstrate using schema to generate documentation.

        Scenario: Team wants to document what data structure
        is needed at each stage.
        """
        # Generate documentation for all stages
        documentation = {}

        for stage in user_onboarding_process.stages:
            stage_id = stage._id
            schema = user_onboarding_process.get_schema(stage_id, partial=True)

            if schema:
                # Create documentation entry
                doc_entry = {
                    "stage_name": stage.name,
                    "properties": {},
                }

                for prop_path, prop_def in schema.items():
                    if prop_def:
                        doc_entry["properties"][prop_path] = {
                            "type": prop_def.get("type", "any"),
                            "default": prop_def.get("default"),
                        }
                    else:
                        doc_entry["properties"][prop_path] = {
                            "type": "any",
                            "default": None,
                        }

                documentation[stage_id] = doc_entry

        # Verify documentation was generated
        assert "registration" in documentation
        assert "verification" in documentation
        assert "profile_setup" in documentation

        # Verify registration stage documentation
        reg_doc = documentation["registration"]
        assert reg_doc["stage_name"] == "Registration"
        assert "email" in reg_doc["properties"]
        assert reg_doc["properties"]["email"]["type"] == "str"

    def test_schema_validation_before_batch_processing(self, user_onboarding_process):
        """Demonstrate pre-validating elements before batch processing.

        Scenario: Processing many elements and want to identify
        invalid ones before expensive evaluation.
        """
        # Create a batch of elements with varying completeness
        elements = [
            DictElement({"email": "user1@example.com", "password": "pass1"}),  # Valid
            DictElement({"email": "user2@example.com"}),  # Missing password
            DictElement({"password": "pass3"}),  # Missing email
            DictElement({"email": "user4@example.com", "password": "pass4"}),  # Valid
            DictElement({}),  # Missing both
        ]

        # Get schema for pre-validation
        schema = user_onboarding_process.get_schema("registration", partial=True)

        # Pre-validate elements against schema
        valid_elements = []
        invalid_elements = []

        for element in elements:
            is_valid = True
            for prop_path in schema.keys():
                if not element.has_property(prop_path):
                    is_valid = False
                    break

            if is_valid:
                valid_elements.append(element)
            else:
                invalid_elements.append(element)

        # Verify we can filter elements before expensive evaluation
        assert len(valid_elements) == 2  # Only 2 valid elements
        assert len(invalid_elements) == 3  # 3 invalid elements

        # Now we can process only valid elements
        for element in valid_elements:
            result = user_onboarding_process.evaluate(element, "registration")
            assert result["stage_result"].status != "incomplete"

    def test_schema_helps_with_data_migration(self, user_onboarding_process):
        """Demonstrate using schema for data migration planning.

        Scenario: Updating process definition and need to migrate
        existing elements to new schema.
        """
        # Old process (before update) - simpler schema
        old_config: ProcessDefinition = {
            "name": "user_onboarding_old",
            "description": "Old user onboarding process",
            "initial_stage": "registration",
            "final_stage": "active",
            "stages": {
                "registration": {
                    "name": "Registration",
                    "expected_properties": {
                        "email": {"type": "str", "default": None},
                    },
                    "gates": [
                        {
                            "name": "to_active",
                            "target_stage": "active",
                            "parent_stage": "registration",
                            "locks": [
                                {
                                    "type": LockType.EXISTS,
                                    "property_path": "email",
                                    "expected_value": None,
                                }
                            ],
                        }
                    ],
                    "expected_actions": [],
                    "is_final": False,
                },
                "active": {
                    "name": "Active",
                    "expected_properties": {},
                    "gates": [],
                    "expected_actions": [],
                    "is_final": True,
                },
            },
        }
        old_process = Process(old_config)

        # Compare schemas for migration planning
        old_schema = old_process.get_schema("registration", partial=True)
        new_schema = user_onboarding_process.get_schema("registration", partial=True)

        # Identify new required properties
        new_properties = set(new_schema.keys()) - set(old_schema.keys())

        # Verify we can identify migration requirements
        assert "password" in new_properties

        # This tells us that existing elements need a "password" field
        # to work with the new process definition
        migration_requirements = []
        for prop_path in new_properties:
            prop_def = new_schema[prop_path]
            migration_requirements.append(
                {
                    "property": prop_path,
                    "type": prop_def["type"] if prop_def else "unknown",
                    "has_default": prop_def.get("default") is not None
                    if prop_def
                    else False,
                }
            )

        assert len(migration_requirements) == 1
        assert migration_requirements[0]["property"] == "password"

    def test_schema_with_nested_properties(self, user_onboarding_process):
        """Demonstrate schema handling for nested property paths.

        Scenario: Working with nested data structures like profile.first_name
        """
        # Get schema for profile_setup stage
        schema = user_onboarding_process.get_schema("profile_setup", partial=True)

        # Verify nested properties are in schema (as nested dict structure)
        assert "profile" in schema
        assert isinstance(schema["profile"], dict)
        assert "first_name" in schema["profile"]
        assert "last_name" in schema["profile"]
        assert "age" in schema["profile"]

        # Create element with nested structure
        element = DictElement(
            {
                "profile": {
                    "first_name": "John",
                    "last_name": "Doe",
                    "age": 25,
                }
            }
        )

        # Verify nested properties are accessible using dot notation
        assert element.has_property("profile.first_name")
        assert element.has_property("profile.last_name")
        assert element.has_property("profile.age")

        # Evaluate successfully
        result = user_onboarding_process.evaluate(element, "profile_setup")
        assert result["stage_result"].status != "incomplete"

    def test_schema_with_defaults_guides_optional_properties(
        self, user_onboarding_process
    ):
        """Demonstrate using default values from schema for optional properties.

        Scenario: Understanding which properties are optional (have defaults)
        vs required (no defaults).
        """
        # Get schema with defaults
        schema = user_onboarding_process.get_schema("profile_setup", partial=True)

        # Helper function to flatten nested schema with defaults
        def flatten_schema_with_defaults(schema_dict, prefix=""):
            optional = {}
            required = []
            for key, value in schema_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    if "type" in value or "default" in value:
                        # This is a property definition
                        if value.get("default") is not None:
                            optional[full_key] = value["default"]
                        else:
                            required.append(full_key)
                    else:
                        # This is a nested structure
                        nested_optional, nested_required = flatten_schema_with_defaults(
                            value, full_key
                        )
                        optional.update(nested_optional)
                        required.extend(nested_required)
            return optional, required

        optional_properties, required_properties = flatten_schema_with_defaults(schema)

        # Verify we can distinguish optional from required
        assert "profile.age" in optional_properties
        assert optional_properties["profile.age"] == 18  # Has default

        assert "profile.first_name" in required_properties
        assert "profile.last_name" in required_properties

        # This helps users understand what's strictly required
        # vs what can be omitted (will use default)
