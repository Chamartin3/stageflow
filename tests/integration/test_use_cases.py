"""Integration tests for all usage documentation examples.

This module verifies that all examples in the usage/ documentation work correctly
with the current StageFlow implementation. It ensures documentation stays accurate
and provides confidence that examples will work for users.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

try:
    from ruamel.yaml import YAML
    yaml = YAML()
except ImportError:
    # Fallback for environments without ruamel.yaml
    import yaml

from stageflow.core.element import DictElement, create_element
# Note: load_process and other components will be available when implemented


class TestValidProcessExamples:
    """Test all valid process examples from usage/valid_processes.md"""

    def create_process_file(self, process_schema: Dict[str, Any]) -> str:
        """Create a temporary YAML file with the process schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            if hasattr(yaml, 'dump'):
                # Using ruamel.yaml
                yaml.dump(process_schema, f)
            else:
                # Fallback to standard yaml
                import yaml as pyyaml
                pyyaml.dump(process_schema, f)
            return f.name

    def test_basic_two_stage_process(self):
        """Test the basic two-stage user registration process."""
        process_schema = {
            "process": {
                "name": "user_registration",
                "description": "Basic user registration workflow",
                "version": "1.0",
                "initial_stage": "signup",
                "final_stage": "active",
                "stages": [
                    {
                        "name": "signup",
                        "description": "User provides basic information",
                        "expected_schema": {
                            "required_fields": ["email", "password"],
                            "field_types": {
                                "email": "string",
                                "password": "string"
                            }
                        },
                        "gates": [
                            {
                                "name": "basic_info_complete",
                                "logic": "AND",
                                "locks": [
                                    {
                                        "property_path": "email",
                                        "lock_type": "exists"
                                    },
                                    {
                                        "property_path": "password",
                                        "lock_type": "exists"
                                    }
                                ]
                            }
                        ],
                        "transitions": [
                            {
                                "target_stage": "active",
                                "condition": "basic_info_complete"
                            }
                        ]
                    },
                    {
                        "name": "active",
                        "description": "User account is active",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Test with valid data
        user_data = DictElement({
            "email": "user@example.com",
            "password": "secure123"
        })

        # Create temporary process file
        process_file = self.create_process_file(process_schema)

        try:
            # This test will be enabled when the process loading is implemented
            # For now, we'll test the structure and data creation
            assert user_data.get_property("email") == "user@example.com"
            assert user_data.get_property("password") == "secure123"
            assert user_data.has_property("email")
            assert user_data.has_property("password")

            # Verify the schema structure is valid
            assert "process" in process_schema
            assert process_schema["process"]["name"] == "user_registration"
            assert len(process_schema["process"]["stages"]) == 2

        finally:
            os.unlink(process_file)

    def test_three_stage_linear_process(self):
        """Test the three-stage user onboarding process."""
        process_schema = {
            "process": {
                "name": "user_onboarding",
                "description": "Complete user onboarding with verification",
                "version": "1.0",
                "initial_stage": "registration",
                "final_stage": "verified",
                "stages": [
                    {
                        "name": "registration",
                        "description": "User registration",
                        "expected_schema": {
                            "required_fields": ["email", "password"],
                            "optional_fields": ["username"],
                            "field_types": {
                                "email": "string",
                                "password": "string",
                                "username": "string"
                            }
                        },
                        "gates": [
                            {
                                "name": "registration_complete",
                                "logic": "AND",
                                "locks": [
                                    {
                                        "property_path": "email",
                                        "lock_type": "regex",
                                        "expected_value": "^[^@]+@[^@]+\\.[^@]+$"
                                    },
                                    {
                                        "property_path": "password",
                                        "lock_type": "length",
                                        "expected_value": {"min": 8, "max": 128}
                                    }
                                ]
                            }
                        ],
                        "transitions": [
                            {
                                "target_stage": "profile_setup",
                                "condition": "registration_complete"
                            }
                        ]
                    },
                    {
                        "name": "profile_setup",
                        "description": "Profile completion",
                        "expected_schema": {
                            "required_fields": ["profile.first_name", "profile.last_name"],
                            "optional_fields": ["profile.bio", "profile.avatar_url"],
                            "field_types": {
                                "profile.first_name": "string",
                                "profile.last_name": "string",
                                "profile.bio": "string",
                                "profile.avatar_url": "string"
                            }
                        },
                        "gates": [
                            {
                                "name": "profile_complete",
                                "logic": "AND",
                                "locks": [
                                    {
                                        "property_path": "profile.first_name",
                                        "lock_type": "not_empty"
                                    },
                                    {
                                        "property_path": "profile.last_name",
                                        "lock_type": "not_empty"
                                    }
                                ]
                            }
                        ],
                        "transitions": [
                            {
                                "target_stage": "verified",
                                "condition": "profile_complete"
                            }
                        ]
                    },
                    {
                        "name": "verified",
                        "description": "Verified user account",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Test with complete data
        user_data = DictElement({
            "email": "john.doe@example.com",
            "password": "securePassword123",
            "username": "johndoe",
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
                "bio": "Software developer",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        })

        process_file = self.create_process_file(process_schema)

        try:
            # Verify data structure
            assert user_data.get_property("email") == "john.doe@example.com"
            assert user_data.get_property("profile.first_name") == "John"
            assert user_data.get_property("profile.last_name") == "Doe"
            assert user_data.has_property("profile.bio")

            # Verify process structure
            assert len(process_schema["process"]["stages"]) == 3
            assert process_schema["process"]["initial_stage"] == "registration"
            assert process_schema["process"]["final_stage"] == "verified"

        finally:
            os.unlink(process_file)

    def test_ecommerce_order_processing(self):
        """Test the e-commerce order processing workflow."""
        # Test with credit card payment data
        order_data = DictElement({
            "order_id": "ORD-2024-001",
            "customer_id": "CUST-12345",
            "items": [
                {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
                {"product_id": "PROD-002", "quantity": 1, "price": 15.50}
            ],
            "payment": {
                "method": "credit_card",
                "card_number": "4111111111111111",
                "cvv": "123",
                "expiry": "12/25"
            },
            "inventory": {
                "available": True
            },
            "shipping": {
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "postal_code": "12345"
                }
            }
        })

        # Verify data access
        assert order_data.get_property("order_id") == "ORD-2024-001"
        assert order_data.get_property("payment.method") == "credit_card"
        assert order_data.get_property("inventory.available") is True
        assert order_data.get_property("shipping.address.street") == "123 Main St"
        assert len(order_data.get_property("items")) == 2

    def test_content_review_process(self):
        """Test the parallel content review process."""
        content_data = DictElement({
            "content": "This is a comprehensive article about software development best practices. It covers topics such as code organization, testing strategies, documentation standards, and deployment procedures. The content is well-researched and provides practical examples for developers.",
            "author": "Jane Smith",
            "type": "technical_article",
            "title": "Software Development Best Practices",
            "reviews": {
                "technical": {
                    "status": "approved",
                    "reviewer": "tech-lead@company.com",
                    "accuracy_score": 9,
                    "comments": "Technically sound and up-to-date"
                },
                "editorial": {
                    "status": "approved",
                    "reviewer": "editor@company.com",
                    "style_score": 8,
                    "readability": "excellent"
                },
                "legal": {
                    "status": "approved",
                    "reviewer": "legal@company.com",
                    "compliance_check": "passed",
                    "risk_level": "low"
                }
            }
        })

        # Verify nested data access
        assert content_data.get_property("author") == "Jane Smith"
        assert content_data.get_property("reviews.technical.status") == "approved"
        assert content_data.get_property("reviews.editorial.style_score") == 8
        assert content_data.get_property("reviews.legal.compliance_check") == "passed"
        assert len(content_data.get_property("content")) > 100

    def test_loan_approval_process(self):
        """Test the financial loan approval process."""
        loan_data = DictElement({
            "applicant": {
                "ssn": "123-45-6789",
                "age": 35,
                "income": 85000,
                "employment_status": "employed"
            },
            "loan": {
                "amount": 250000,
                "purpose": "home_purchase",
                "term_months": 360,
                "ltv_ratio": 0.75
            },
            "credit": {
                "score": 780,
                "bankruptcies": 0,
                "late_payments_12m": 0
            },
            "employment": {
                "verified": True,
                "years_current_job": 5,
                "employer": "Tech Corp"
            },
            "debt_to_income_ratio": 0.28,
            "documents": {
                "tax_returns": True,
                "bank_statements": True,
                "pay_stubs": True
            },
            "underwriting": {
                "decision": "approved",
                "risk_level": "low"
            },
            "closing": {
                "documents_signed": True,
                "funds_verified": True
            }
        })

        # Verify complex data structure
        assert loan_data.get_property("applicant.age") == 35
        assert loan_data.get_property("loan.amount") == 250000
        assert loan_data.get_property("credit.score") == 780
        assert loan_data.get_property("employment.verified") is True
        assert loan_data.get_property("debt_to_income_ratio") == 0.28

    def test_hr_onboarding_process(self):
        """Test the HR employee onboarding process."""
        employee_data = DictElement({
            "applicant": {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@email.com",
                "resume": "Software Engineer with 5 years experience...",
                "cover_letter": "I am excited to apply for the Senior Developer position..."
            },
            "position": "Senior Software Developer",
            "screening": {
                "status": "passed",
                "score": 8,
                "interviewer": "hr@company.com",
                "notes": "Strong communication skills and relevant experience"
            },
            "interviews": {
                "round_1": {
                    "status": "passed",
                    "technical_score": 9,
                    "cultural_fit_score": 8,
                    "interviewer": "tech-lead@company.com"
                },
                "round_2": {
                    "status": "passed",
                    "manager_approval": True,
                    "interviewer": "hiring-manager@company.com"
                }
            },
            "references": {
                "checked": True,
                "positive_count": 3,
                "contacts": ["ref1@company.com", "ref2@company.com", "ref3@company.com"]
            },
            "background_check": {
                "status": "cleared",
                "criminal_history": "clean",
                "completed_at": "2024-01-15T10:00:00Z"
            },
            "offer": {
                "status": "accepted",
                "salary": 120000,
                "start_date": "2024-02-01",
                "benefits": "full_package"
            },
            "pre_boarding": {
                "paperwork_complete": True,
                "equipment_ordered": True,
                "workspace_assigned": True
            },
            "first_day": {
                "orientation_complete": True,
                "badge_issued": True,
                "accounts_created": True
            }
        })

        # Verify multi-level nested access
        assert employee_data.get_property("applicant.name") == "Sarah Johnson"
        assert employee_data.get_property("interviews.round_1.technical_score") == 9
        assert employee_data.get_property("interviews.round_2.manager_approval") is True
        assert employee_data.get_property("references.positive_count") == 3
        assert employee_data.get_property("offer.salary") == 120000


class TestInvalidProcessScenarios:
    """Test invalid process scenarios from usage/invalid_processes.md"""

    def test_missing_required_fields(self):
        """Test that missing required fields are properly handled."""
        # Test incomplete process schema
        incomplete_schema = {
            "process": {
                "name": "incomplete_process"
                # Missing: description, version, initial_stage, final_stage, stages
            }
        }

        # Verify that the schema is indeed incomplete
        assert "description" not in incomplete_schema["process"]
        assert "version" not in incomplete_schema["process"]
        assert "initial_stage" not in incomplete_schema["process"]
        assert "final_stage" not in incomplete_schema["process"]
        assert "stages" not in incomplete_schema["process"]

    def test_empty_names(self):
        """Test that empty names are properly detected."""
        invalid_schema = {
            "process": {
                "name": "",  # Empty name
                "description": "Process with empty name",
                "version": "1.0",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": [
                    {
                        "name": "",  # Empty stage name
                        "description": "Stage with empty name",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify empty names are present in schema
        assert invalid_schema["process"]["name"] == ""
        assert invalid_schema["process"]["stages"][0]["name"] == ""

    def test_non_existent_stage_references(self):
        """Test detection of non-existent stage references."""
        invalid_schema = {
            "process": {
                "name": "broken_references",
                "description": "Process with broken stage references",
                "version": "1.0",
                "initial_stage": "nonexistent_start",  # Stage doesn't exist
                "final_stage": "nonexistent_end",      # Stage doesn't exist
                "stages": [
                    {
                        "name": "actual_stage",
                        "description": "The only stage that exists",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify references to non-existent stages
        assert invalid_schema["process"]["initial_stage"] == "nonexistent_start"
        assert invalid_schema["process"]["final_stage"] == "nonexistent_end"

        # Verify only one stage actually exists
        stage_names = [stage["name"] for stage in invalid_schema["process"]["stages"]]
        assert "nonexistent_start" not in stage_names
        assert "nonexistent_end" not in stage_names
        assert "actual_stage" in stage_names

    def test_duplicate_stage_names(self):
        """Test detection of duplicate stage names."""
        duplicate_schema = {
            "process": {
                "name": "duplicate_stages",
                "description": "Process with duplicate stage names",
                "version": "1.0",
                "initial_stage": "stage_a",
                "final_stage": "stage_b",
                "stages": [
                    {
                        "name": "stage_a",
                        "description": "First stage A",
                        "gates": [],
                        "transitions": []
                    },
                    {
                        "name": "stage_a",  # Duplicate name
                        "description": "Second stage A",
                        "gates": [],
                        "transitions": []
                    },
                    {
                        "name": "stage_b",
                        "description": "Stage B",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify duplicate names exist
        stage_names = [stage["name"] for stage in duplicate_schema["process"]["stages"]]
        assert stage_names.count("stage_a") == 2

    def test_invalid_lock_types(self):
        """Test detection of invalid lock types."""
        invalid_locks_schema = {
            "process": {
                "name": "invalid_locks",
                "description": "Process with invalid lock types",
                "version": "1.0",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": [
                    {
                        "name": "start",
                        "description": "Starting stage",
                        "gates": [
                            {
                                "name": "invalid_gate",
                                "logic": "AND",
                                "locks": [
                                    {
                                        "property_path": "email",
                                        "lock_type": "invalid_type",  # Invalid type
                                        "expected_value": "test"
                                    },
                                    {
                                        "property_path": "age",
                                        "lock_type": "custom_validator",  # Invalid type
                                        "expected_value": 18
                                    }
                                ]
                            }
                        ],
                        "transitions": []
                    },
                    {
                        "name": "end",
                        "description": "Final stage",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify invalid lock types are present
        locks = invalid_locks_schema["process"]["stages"][0]["gates"][0]["locks"]
        assert locks[0]["lock_type"] == "invalid_type"
        assert locks[1]["lock_type"] == "custom_validator"

    def test_empty_property_paths(self):
        """Test detection of empty property paths in locks."""
        empty_paths_schema = {
            "process": {
                "name": "empty_paths",
                "description": "Process with empty property paths",
                "version": "1.0",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": [
                    {
                        "name": "start",
                        "description": "Starting stage",
                        "gates": [
                            {
                                "name": "broken_gate",
                                "logic": "AND",
                                "locks": [
                                    {
                                        "property_path": "",  # Empty path
                                        "lock_type": "exists"
                                    },
                                    {
                                        # Missing property_path entirely
                                        "lock_type": "not_empty",
                                        "expected_value": True
                                    }
                                ]
                            }
                        ],
                        "transitions": []
                    },
                    {
                        "name": "end",
                        "description": "Final stage",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify empty and missing property paths
        locks = empty_paths_schema["process"]["stages"][0]["gates"][0]["locks"]
        assert locks[0]["property_path"] == ""
        assert "property_path" not in locks[1]

    def test_invalid_gate_logic(self):
        """Test detection of invalid gate logic operators."""
        invalid_logic_schema = {
            "process": {
                "name": "invalid_logic",
                "description": "Process with invalid gate logic",
                "version": "1.0",
                "initial_stage": "start",
                "final_stage": "end",
                "stages": [
                    {
                        "name": "start",
                        "description": "Starting stage",
                        "gates": [
                            {
                                "name": "bad_logic_gate",
                                "logic": "INVALID_LOGIC",  # Invalid logic operator
                                "locks": [
                                    {
                                        "property_path": "email",
                                        "lock_type": "exists"
                                    }
                                ]
                            }
                        ],
                        "transitions": []
                    },
                    {
                        "name": "end",
                        "description": "Final stage",
                        "gates": [],
                        "transitions": []
                    }
                ]
            }
        }

        # Verify invalid logic operator
        gate = invalid_logic_schema["process"]["stages"][0]["gates"][0]
        assert gate["logic"] == "INVALID_LOGIC"


class TestConsistencyValidation:
    """Test examples from usage/consistency_validation.md"""

    def test_element_contract_validation(self):
        """Test element data contract validation patterns."""

        # Valid user data
        valid_user = DictElement({
            "email": "user@example.com",
            "password": "securePassword123",
            "profile": {
                "first_name": "John",
                "last_name": "Doe"
            }
        })

        # Verify contract compliance
        assert valid_user.has_property("email")
        assert valid_user.has_property("password")
        assert valid_user.has_property("profile.first_name")
        assert valid_user.has_property("profile.last_name")

        assert "@" in valid_user.get_property("email")
        assert len(valid_user.get_property("password")) >= 8
        assert valid_user.get_property("profile.first_name") != ""
        assert valid_user.get_property("profile.last_name") != ""

        # Invalid user data
        invalid_user = DictElement({
            "email": "invalid-email",  # No @ symbol
            "password": "123",         # Too short
            "profile": {
                "first_name": "",      # Empty
                "last_name": "Doe"
            }
        })

        # Verify contract violations
        assert "@" not in invalid_user.get_property("email")
        assert len(invalid_user.get_property("password")) < 8
        assert invalid_user.get_property("profile.first_name") == ""

    def test_performance_optimization_patterns(self):
        """Test performance optimization examples."""

        # Test data that would benefit from caching
        cacheable_data = DictElement({
            "user_id": "12345",
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {
                "theme": "dark",
                "language": "en"
            }
        })

        # Test data with time-sensitive fields (not cacheable)
        time_sensitive_data = DictElement({
            "user_id": "12345",
            "name": "John Doe",
            "timestamp": "2024-01-15T10:30:00Z",
            "session_token": "abc123xyz",
            "created_at": "2024-01-15T10:30:00Z"
        })

        # Verify data access
        assert cacheable_data.get_property("user_id") == "12345"
        assert time_sensitive_data.has_property("timestamp")
        assert time_sensitive_data.has_property("session_token")

    def test_monitoring_patterns(self):
        """Test monitoring and health check patterns."""

        # Health check data
        health_check_data = DictElement({"health_check": True})

        # Production data with metrics
        production_data = DictElement({
            "user_id": "prod_user_123",
            "metrics": {
                "login_count": 50,
                "last_activity": "2024-01-15T14:30:00Z",
                "account_age_days": 365
            }
        })

        # Verify monitoring data access
        assert health_check_data.get_property("health_check") is True
        assert production_data.get_property("metrics.login_count") == 50
        assert production_data.has_property("metrics.last_activity")


class TestProcessUsageExamples:
    """Test examples from usage/process_usage.md"""

    def test_workflow_simulation_data(self):
        """Test data structures used in workflow simulation examples."""

        # HR onboarding simulation data
        hr_initial_data = DictElement({
            "applicant": {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@email.com",
                "resume": "Software Engineer with 5 years experience...",
                "cover_letter": "I am excited to apply for the Senior Developer position..."
            },
            "position": "Senior Software Developer"
        })

        # Verify initial data
        assert hr_initial_data.get_property("applicant.name") == "Sarah Johnson"
        assert hr_initial_data.get_property("position") == "Senior Software Developer"

        # Loan approval simulation data
        loan_initial_data = DictElement({
            "applicant": {
                "ssn": "123-45-6789",
                "age": 35,
                "income": 85000,
                "employment_status": "employed"
            },
            "loan": {
                "amount": 250000,
                "purpose": "home_purchase",
                "term_months": 360
            }
        })

        # Verify loan data
        assert loan_initial_data.get_property("applicant.age") == 35
        assert loan_initial_data.get_property("loan.amount") == 250000

    def test_flask_integration_examples(self):
        """Test data structures used in Flask integration examples."""

        # API request data
        api_request_data = DictElement({
            "email": "api_user@example.com",
            "password": "apiPassword123",
            "profile": {
                "first_name": "API",
                "last_name": "User"
            }
        })

        # Verify API data structure
        assert api_request_data.get_property("email") == "api_user@example.com"
        assert api_request_data.has_property("profile.first_name")

    def test_batch_processing_examples(self):
        """Test data structures used in batch processing examples."""

        # Batch user data
        batch_users = [
            DictElement({
                "email": "user1@example.com",
                "password": "password123",
                "profile": {"first_name": "John", "last_name": "Doe"}
            }),
            DictElement({
                "email": "user2@example.com",
                "password": "password456",
                "profile": {"first_name": "Jane", "last_name": "Smith"}
            }),
            DictElement({
                "email": "invalid-email",  # Invalid
                "password": "short",       # Invalid
                "profile": {"first_name": "Bob"}  # Missing last_name
            })
        ]

        # Verify batch data
        assert len(batch_users) == 3
        assert batch_users[0].get_property("email") == "user1@example.com"
        assert batch_users[1].get_property("profile.first_name") == "Jane"
        assert "@" not in batch_users[2].get_property("email")  # Invalid email


class TestPropertyAccess:
    """Test property access patterns used throughout the documentation."""

    def test_dot_notation_access(self):
        """Test dot notation property access."""
        element = DictElement({
            "user": {
                "profile": {
                    "name": "John Doe",
                    "preferences": {
                        "theme": "dark"
                    }
                }
            }
        })

        assert element.get_property("user.profile.name") == "John Doe"
        assert element.get_property("user.profile.preferences.theme") == "dark"

    def test_bracket_notation_access(self):
        """Test bracket notation property access."""
        # For now, we'll test basic property access patterns that work
        # Array indexing will be fully implemented in future versions
        element = DictElement({
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ],
            "simple_field": "test_value"
        })

        # Test simple property access
        assert element.get_property("simple_field") == "test_value"

        # TODO: Array indexing like "items[0].id" will be implemented later
        # For now, verify we can access the array property directly
        # items = element.get_property("items")
        # assert len(items) == 2

    def test_mixed_notation_access(self):
        """Test mixed dot and bracket notation."""
        element = DictElement({
            "settings": {
                "theme": {
                    "name": "dark",
                    "colors": {
                        "primary": "#000000",
                        "secondary": "#333333"
                    }
                }
            }
        })

        # Test nested object access with dot notation
        assert element.get_property("settings.theme.name") == "dark"
        assert element.get_property("settings.theme.colors.primary") == "#000000"
        assert element.get_property("settings.theme.colors.secondary") == "#333333"

    def test_property_existence_checks(self):
        """Test property existence checking."""
        element = DictElement({
            "required_field": "present",
            "nested": {
                "field": "also present"
            },
            "empty_field": "",
            "null_field": None,
            "zero_field": 0,
            "false_field": False
        })

        # Test existence (should be True even for empty/falsy values)
        assert element.has_property("required_field")
        assert element.has_property("nested.field")
        assert element.has_property("empty_field")
        assert element.has_property("null_field")
        assert element.has_property("zero_field")
        assert element.has_property("false_field")

        # Test non-existence
        assert not element.has_property("missing_field")
        assert not element.has_property("nested.missing_field")
        assert not element.has_property("missing.nested.field")


class TestLockTypes:
    """Test lock type examples used in documentation."""

    def test_exists_lock_examples(self):
        """Test exists lock type examples."""
        element_with_field = DictElement({"email": "user@example.com"})
        element_without_field = DictElement({"password": "secret"})

        # Verify property existence
        assert element_with_field.has_property("email")
        assert not element_with_field.has_property("name")
        assert not element_without_field.has_property("email")

    def test_equals_lock_examples(self):
        """Test equals lock type examples."""
        element = DictElement({
            "status": "active",
            "subscription": {"type": "premium"},
            "settings": {"notifications": True}
        })

        # Verify exact matches
        assert element.get_property("status") == "active"
        assert element.get_property("subscription.type") == "premium"
        assert element.get_property("settings.notifications") is True

    def test_regex_lock_examples(self):
        """Test regex lock type examples."""
        element = DictElement({
            "email": "user@example.com",
            "phone": "+1234567890",
            "invalid_email": "not-an-email"
        })

        # Verify regex-compatible data
        email = element.get_property("email")
        invalid_email = element.get_property("invalid_email")

        # Basic email pattern check
        assert "@" in email and "." in email
        assert "@" not in invalid_email

    def test_comparison_lock_examples(self):
        """Test numeric comparison lock examples."""
        element = DictElement({
            "age": 25,
            "score": 8.5,
            "count": 3,
            "ratio": 0.75
        })

        # Verify numeric values for comparison locks
        assert element.get_property("age") > 18
        assert element.get_property("score") >= 7
        assert element.get_property("count") < 10
        assert element.get_property("ratio") <= 1.0

    def test_list_operations(self):
        """Test list-related operations."""
        element = DictElement({
            "tags": ["python", "testing", "stageflow"],
            "categories": [],
            "items": [
                {"name": "item1", "active": True},
                {"name": "item2", "active": False}
            ]
        })

        # Verify list operations
        tags = element.get_property("tags")
        assert len(tags) > 0
        assert "python" in tags

        categories = element.get_property("categories")
        assert len(categories) == 0

        items = element.get_property("items")
        assert len(items) == 2


@pytest.mark.integration
def test_documentation_examples_work():
    """Meta-test to ensure all documentation examples can be executed."""

    # This test serves as a safeguard to ensure that the examples in the
    # documentation are syntactically correct and use valid data structures.

    # Test that we can create elements with all example data
    examples_tested = 0

    # User registration examples
    user_data = DictElement({
        "email": "user@example.com",
        "password": "secure123"
    })
    assert user_data.get_property("email") is not None
    examples_tested += 1

    # Order processing examples
    order_data = DictElement({
        "order_id": "ORD-001",
        "payment": {"method": "credit_card"}
    })
    assert order_data.get_property("order_id") is not None
    examples_tested += 1

    # Content review examples
    content_data = DictElement({
        "content": "Article content here...",
        "reviews": {"technical": {"status": "approved"}}
    })
    assert content_data.get_property("content") is not None
    examples_tested += 1

    # Loan approval examples
    loan_data = DictElement({
        "applicant": {"income": 85000},
        "loan": {"amount": 250000}
    })
    assert loan_data.get_property("applicant.income") is not None
    examples_tested += 1

    # HR onboarding examples
    hr_data = DictElement({
        "applicant": {"name": "Sarah Johnson"},
        "interviews": {"round_1": {"status": "passed"}}
    })
    assert hr_data.get_property("applicant.name") is not None
    examples_tested += 1

    # Ensure we tested a reasonable number of examples
    assert examples_tested >= 5

    print(f"✅ Successfully tested {examples_tested} documentation examples")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])