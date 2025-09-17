"""Pytest configuration and fixtures for StageFlow tests."""

from typing import Any

import pytest

from stageflow.core.element import DictElement
from stageflow.core.gate import Gate, GateLogic
from stageflow.core.lock import Lock, LockType
from stageflow.core.process import Process
from stageflow.core.schema import ItemSchema
from stageflow.core.stage import Stage


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
        property_path="email",
        lock_type=LockType.EXISTS,
    )


@pytest.fixture
def email_lock() -> Lock:
    """Email validation lock for testing."""
    return Lock(
        property_path="email",
        lock_type=LockType.REGEX,
        expected_value=r"^[^@]+@[^@]+\.[^@]+$",
    )


@pytest.fixture
def basic_gate(basic_lock) -> Gate:
    """Basic gate for testing."""
    return Gate(
        name="basic_validation",
        locks=[basic_lock],
        logic=GateLogic.AND,
    )


@pytest.fixture
def email_gate(email_lock) -> Gate:
    """Email validation gate for testing."""
    return Gate(
        name="email_validation",
        locks=[email_lock],
        logic=GateLogic.AND,
    )


@pytest.fixture
def basic_schema() -> ItemSchema:
    """Basic schema for testing."""
    return ItemSchema(
        name="basic_schema",
        required_fields={"email", "user_id"},
        optional_fields={"profile.first_name", "profile.last_name"},
        field_types={"email": "string", "user_id": "string"},
    )


@pytest.fixture
def basic_stage(basic_gate, basic_schema) -> Stage:
    """Basic stage for testing."""
    return Stage(
        name="registration",
        gates=[basic_gate],
        schema=basic_schema,
    )


@pytest.fixture
def multi_stage_process(basic_stage) -> Process:
    """Multi-stage process for testing."""
    # Create additional stages
    profile_lock = Lock(
        property_path="profile.first_name",
        lock_type=LockType.EXISTS,
    )
    profile_gate = Gate(
        name="profile_complete",
        locks=[profile_lock],
        logic=GateLogic.AND,
    )
    profile_stage = Stage(
        name="profile_setup",
        gates=[profile_gate],
    )

    verification_lock = Lock(
        property_path="verification.email_verified",
        lock_type=LockType.EQUALS,
        expected_value=True,
    )
    verification_gate = Gate(
        name="email_verified",
        locks=[verification_lock],
        logic=GateLogic.AND,
    )
    verification_stage = Stage(
        name="verification",
        gates=[verification_gate],
    )

    return Process(
        name="user_onboarding",
        stages=[basic_stage, profile_stage, verification_stage],
        stage_order=["registration", "profile_setup", "verification"],
    )


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
