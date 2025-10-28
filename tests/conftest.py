"""Pytest configuration and fixtures for StageFlow tests.

This module provides shared fixtures and pytest configuration for the StageFlow
test suite. It imports fixtures from specialized modules and provides backwards
compatibility with existing tests.
"""

from typing import Any

import pytest

# from stageflow import Process
from stageflow.element import DictElement
from stageflow.gate import Gate
from stageflow.lock import Lock, LockType

# from stageflow.process.schema.core import ItemSchema
# from stageflow.stage import Stage

# Import fixtures from specialized modules
# These imports make fixtures available to all test modules
# pytest_plugins = [
#     "tests.fixtures.core_models",
#     "tests.fixtures.sample_data",
#     "tests.fixtures.process_schemas",
#     "tests.fixtures.mock_objects",
#     "tests.fixtures.parameters"
# ]


@pytest.fixture
def sample_process_file(tmp_path):
    """Create a temporary process file for CLI testing."""

    process_content = {
        "name": "test_process",
        "stage_order": ["stage1", "stage2", "stage3"],
        "stages": {
            "stage1": {
                "gates": {
                    "gate1": {
                        "logic": "and",
                        "locks": [{"property": "field1", "type": "exists"}],
                    }
                }
            },
            "stage2": {
                "gates": {
                    "gate2": {
                        "logic": "and",
                        "locks": [
                            {"property": "field1", "type": "exists"},
                            {"property": "field2", "type": "exists"},
                        ],
                    }
                }
            },
            "stage3": {
                "gates": {
                    "gate3": {
                        "logic": "and",
                        "locks": [
                            {
                                "property": "field3",
                                "type": "equals",
                                "value": "completed",
                            }
                        ],
                    }
                }
            },
        },
    }

    # Write as YAML file
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.default_flow_style = False
    process_file = tmp_path / "test_process.yaml"
    with open(process_file, "w") as f:
        yaml.dump(process_content, f)

    return process_file


@pytest.fixture
def sample_element_file(tmp_path):
    """Create a temporary element file for CLI testing."""
    import json

    element_data = {
        "field1": "value1",
        "field2": "value2",
        "user_id": "user123",
        "email": "test@example.com",
    }

    element_file = tmp_path / "test_element.json"
    with open(element_file, "w") as f:
        json.dump(element_data, f, indent=2)

    return element_file


@pytest.fixture
def sample_element_data() -> dict[str, Any]:
    """Sample element data for testing."""
    return {
        "user_id": "user123",
        "email": "test@example.com",
        "profile": {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
        },
        "preferences": {
            "newsletter": True,
            "notifications": False,
        },
        "verification": {
            "email_verified": True,
            "phone_verified": False,
        },
        "metadata": {
            "signup_date": "2024-01-15",
            "last_login": "2024-01-20",
        },
    }


@pytest.fixture
def sample_element(sample_element_data) -> DictElement:
    """Sample element instance for testing."""
    return DictElement(sample_element_data)


@pytest.fixture
def basic_lock() -> Lock:
    """Basic lock for testing."""
    return Lock(
        {
            "property_path": "email",
            "type": LockType.EXISTS,
        }
    )


@pytest.fixture
def email_lock() -> Lock:
    """Email validation lock for testing."""
    return Lock(
        {
            "property_path": "email",
            "type": LockType.REGEX,
            "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
        }
    )


@pytest.fixture
def basic_gate() -> Gate:
    """Basic gate for testing."""
    return Gate(
        {
            "name": "basic_validation",
            "description": "Basic validation gate",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [{"exists": "email"}],
        }
    )


@pytest.fixture
def email_gate() -> Gate:
    """Email validation gate for testing."""
    return Gate(
        {
            "name": "email_validation",
            "description": "Email validation gate",
            "target_stage": "email_verified",
            "parent_stage": "unverified",
            "locks": [
                {
                    "type": LockType.REGEX,
                    "property_path": "email",
                    "expected_value": r"^[^@]+@[^@]+\.[^@]+$",
                }
            ],
        }
    )


# @pytest.fixture
# def basic_schema() -> ItemSchema:
#     """Basic schema for testing."""
#     return ItemSchema(
#         name="basic_schema",
#         required_fields={"email", "user_id"},
#         optional_fields={"profile.first_name", "profile.last_name"},
#         field_types={"email": "string", "user_id": "string"},
#     )


# @pytest.fixture
# def basic_stage(basic_gate, basic_schema) -> Stage:
#     """Basic stage for testing."""
#     return Stage(
#         name="registration",
#         gates=[basic_gate],
#         schema=basic_schema,
#     )


# @pytest.fixture
# def multi_stage_process(basic_stage) -> Process:
#     """Multi-stage process for testing."""
#     # Create additional stages
#     profile_lock = Lock({
#         "property_path": "profile.first_name",
#         "type": LockType.EXISTS,
#     })
#     profile_gate = Gate({
#         "name": "profile_complete",
#         "description": "Profile completion gate",
#         "target_stage": "profile_verified",
#         "parent_stage": "profile_pending",
#         "locks": [{"exists": "profile.first_name"}]
#     })

#     verification_lock = Lock({
#         "property_path": "verification.email_verified",
#         "type": LockType.EQUALS,
#         "expected_value": True,
#     })
#     verification_gate = Gate({
#         "name": "email_verified",
#         "description": "Email verification gate",
#         "target_stage": "verified",
#         "parent_stage": "unverified",
#         "locks": [{
#             "type": LockType.EQUALS,
#             "property_path": "verification.email_verified",
#             "expected_value": True
#         }]
#     })

#     return Process(
#         name="user_onboarding",
#         stages=[basic_stage, profile_stage, verification_stage],
#         stage_order=["registration", "profile_setup", "verification"],
#     )


@pytest.fixture
def incomplete_element_data() -> dict[str, Any]:
    """Incomplete element data for testing failure scenarios."""
    return {
        "user_id": "user456",
        # Missing email
        "profile": {
            "first_name": "Jane",
            # Missing last_name
        },
        "verification": {
            "email_verified": False,
            "phone_verified": False,
        },
    }


@pytest.fixture
def incomplete_element(incomplete_element_data) -> DictElement:
    """Incomplete element for testing failure scenarios."""
    return DictElement(incomplete_element_data)


@pytest.fixture
def complex_element_data() -> dict[str, Any]:
    """Complex nested element data for testing."""
    return {
        "order_id": "ORD-12345",
        "customer": {
            "id": "CUST-789",
            "name": "Alice Smith",
            "email": "alice@example.com",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "ST",
                "zip": "12345",
            },
        },
        "items": [
            {
                "id": "ITEM-001",
                "name": "Widget A",
                "quantity": 2,
                "price": 19.99,
            },
            {
                "id": "ITEM-002",
                "name": "Widget B",
                "quantity": 1,
                "price": 39.99,
            },
        ],
        "payment": {
            "method": "credit_card",
            "amount": 79.97,
            "status": "pending",
            "transaction_id": "TXN-ABC123",
        },
        "shipping": {
            "method": "standard",
            "estimated_delivery": "2024-01-25",
            "tracking_number": None,
        },
        "timestamps": {
            "created": "2024-01-20T10:00:00Z",
            "updated": "2024-01-20T10:30:00Z",
        },
    }


@pytest.fixture
def complex_element(complex_element_data) -> DictElement:
    """Complex element for testing advanced scenarios."""
    return DictElement(complex_element_data)


# Note: The fixtures below are maintained for backwards compatibility with existing tests.
# New tests should use the more comprehensive fixtures from the fixtures/ modules which provide:
# - Broader coverage of edge cases and scenarios
# - Better organization by domain (core models, sample data, schemas, mocks)
# - Parameterized fixtures for comprehensive testing
# - Factory fixtures for dynamic test data generation
