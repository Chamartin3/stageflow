"""Core model fixtures for StageFlow testing.

This module provides reusable fixtures for all core StageFlow model objects
including Element, Lock, Gate, Stage, and Process instances configured for
various testing scenarios.
"""

from typing import Any

import pytest

from stageflow.core.element import DictElement, Element, create_element
from stageflow.core.stage import Stage
from stageflow.gates import Gate, GateOperation, Lock, LockType, register_lock_validator as register_validator
from stageflow.process import Process
from stageflow.process.schema.core import ItemSchema


# Element Fixtures
@pytest.fixture
def empty_element() -> DictElement:
    """Empty element for testing edge cases."""
    return DictElement({})


@pytest.fixture
def minimal_user_element() -> DictElement:
    """Minimal user element with only required fields."""
    return DictElement({
        "id": "usr_001",
        "email": "user@example.com"
    })


@pytest.fixture
def complete_user_element() -> DictElement:
    """Complete user element with all common fields."""
    return DictElement({
        "id": "usr_001",
        "email": "user@example.com",
        "username": "testuser",
        "profile": {
            "first_name": "Test",
            "last_name": "User",
            "display_name": "Test User",
            "bio": "A test user for StageFlow testing",
            "avatar_url": "https://example.com/avatar.jpg",
            "phone": "+1-555-0123",
            "birthdate": "1990-01-01",
            "timezone": "UTC"
        },
        "preferences": {
            "email_notifications": True,
            "push_notifications": False,
            "theme": "light",
            "language": "en",
            "privacy": {
                "profile_visibility": "public",
                "email_visibility": "private"
            }
        },
        "verification": {
            "email_verified": True,
            "phone_verified": False,
            "identity_verified": False,
            "verification_date": "2024-01-15T10:00:00Z"
        },
        "metadata": {
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "last_login": "2024-01-20T15:30:00Z",
            "login_count": 42,
            "source": "web",
            "tags": ["premium", "early_adopter"]
        }
    })


@pytest.fixture
def order_element() -> DictElement:
    """Order element for testing complex nested structures."""
    return DictElement({
        "order_id": "ORD-2024-001",
        "customer_id": "usr_001",
        "status": "pending",
        "items": [
            {
                "id": "item_001",
                "name": "Premium Widget",
                "sku": "WID-PREM-001",
                "quantity": 2,
                "unit_price": 29.99,
                "total_price": 59.98,
                "category": "widgets",
                "attributes": {
                    "color": "blue",
                    "size": "medium",
                    "material": "metal"
                }
            },
            {
                "id": "item_002",
                "name": "Basic Widget",
                "sku": "WID-BASIC-001",
                "quantity": 1,
                "unit_price": 19.99,
                "total_price": 19.99,
                "category": "widgets",
                "attributes": {
                    "color": "red",
                    "size": "small",
                    "material": "plastic"
                }
            }
        ],
        "shipping": {
            "method": "standard",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "zip": "12345",
                "country": "US"
            },
            "estimated_delivery": "2024-01-25",
            "tracking_number": None
        },
        "payment": {
            "method": "credit_card",
            "status": "pending",
            "amount": 79.97,
            "currency": "USD",
            "transaction_id": "TXN-ABC123",
            "payment_date": None
        },
        "totals": {
            "subtotal": 79.97,
            "tax": 6.40,
            "shipping": 5.99,
            "discount": 0.00,
            "total": 92.36
        },
        "timestamps": {
            "created": "2024-01-20T10:00:00Z",
            "updated": "2024-01-20T10:30:00Z"
        }
    })


@pytest.fixture
def malformed_element() -> DictElement:
    """Element with various edge cases and malformed data."""
    return DictElement({
        "valid_field": "good_value",
        "empty_string": "",
        "empty_list": [],
        "empty_dict": {},
        "null_field": None,
        "zero_value": 0,
        "false_value": False,
        "nested": {
            "missing_required": None,
            "valid_nested": "value",
            "deeply": {
                "nested": {
                    "value": "deep_value"
                }
            }
        },
        "list_with_mixed": [
            {"valid": True},
            {"invalid": None},
            "",
            None,
            42
        ],
        "special_chars": "!@#$%^&*()[]{}|\\:;\"'<>?/~`",
        "unicode": "测试数据 🚀 émojis",
        "large_number": 999999999999999,
        "negative_number": -42
    })


# Lock Fixtures
@pytest.fixture
def exists_lock() -> Lock:
    """Basic existence check lock."""
    return Lock(
        property_path="email",
        lock_type=LockType.EXISTS
    )


@pytest.fixture
def email_regex_lock() -> Lock:
    """Email format validation lock."""
    return Lock(
        property_path="email",
        lock_type=LockType.REGEX,
        expected_value=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )


@pytest.fixture
def age_range_lock() -> Lock:
    """Age range validation lock."""
    return Lock(
        property_path="profile.age",
        lock_type=LockType.RANGE,
        expected_value=[18, 120]
    )


@pytest.fixture
def status_enum_lock() -> Lock:
    """Status enumeration validation lock."""
    return Lock(
        property_path="status",
        lock_type=LockType.IN_LIST,
        expected_value=["pending", "approved", "rejected", "completed"]
    )


@pytest.fixture
def password_length_lock() -> Lock:
    """Password length validation lock."""
    return Lock(
        property_path="password",
        lock_type=LockType.LENGTH,
        expected_value={"min": 8, "max": 128}
    )


@pytest.fixture
def verified_equals_lock() -> Lock:
    """Verification status exact match lock."""
    return Lock(
        property_path="verification.email_verified",
        lock_type=LockType.EQUALS,
        expected_value=True
    )


@pytest.fixture
def custom_validator_lock() -> Lock:
    """Custom validator lock for testing extensibility."""
    # Register a custom validator for testing
    def validate_strong_password(value: Any, expected: Any) -> bool:
        """Validate password strength."""
        if not isinstance(value, str):
            return False

        has_upper = any(c.isupper() for c in value)
        has_lower = any(c.islower() for c in value)
        has_digit = any(c.isdigit() for c in value)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value)

        return all([has_upper, has_lower, has_digit, has_special])

    register_validator("strong_password", validate_strong_password)

    return Lock(
        property_path="password",
        lock_type=LockType.CUSTOM,
        validator_name="strong_password"
    )


# Gate Fixtures
@pytest.fixture
def simple_and_gate(exists_lock: Lock) -> Gate:
    """Simple AND gate with single lock."""
    return Gate(
        name="email_required",
        locks=[exists_lock],
        logic=GateOperation.AND
    )


@pytest.fixture
def complex_and_gate(email_regex_lock: Lock, password_length_lock: Lock) -> Gate:
    """Complex AND gate with multiple locks."""
    return Gate(
        name="registration_validation",
        locks=[email_regex_lock, password_length_lock],
        logic=GateOperation.AND
    )


@pytest.fixture
def or_gate(exists_lock: Lock, verified_equals_lock: Lock) -> Gate:
    """OR gate for alternative validation paths."""
    return Gate(
        name="email_or_verified",
        locks=[exists_lock, verified_equals_lock],
        logic=GateOperation.OR
    )


@pytest.fixture
def not_gate(status_enum_lock: Lock) -> Gate:
    """NOT gate for exclusion validation."""
    return Gate(
        name="not_completed",
        locks=[status_enum_lock],
        logic=GateOperation.NOT
    )


# Schema Fixtures
@pytest.fixture
def basic_user_schema() -> ItemSchema:
    """Basic user schema for simple validation."""
    return ItemSchema(
        name="basic_user",
        required_fields={"id", "email"},
        optional_fields={"username", "profile.first_name", "profile.last_name"},
        field_types={
            "id": "string",
            "email": "string",
            "username": "string"
        }
    )


@pytest.fixture
def complete_user_schema() -> ItemSchema:
    """Complete user schema with all fields."""
    return ItemSchema(
        name="complete_user",
        required_fields={
            "id", "email", "profile.first_name", "profile.last_name"
        },
        optional_fields={
            "username", "profile.display_name", "profile.bio", "profile.avatar_url",
            "profile.phone", "profile.birthdate", "profile.timezone",
            "preferences.email_notifications", "preferences.push_notifications",
            "preferences.theme", "preferences.language",
            "verification.email_verified", "verification.phone_verified"
        },
        field_types={
            "id": "string",
            "email": "string",
            "username": "string",
            "profile.first_name": "string",
            "profile.last_name": "string",
            "verification.email_verified": "boolean"
        }
    )


@pytest.fixture
def order_schema() -> ItemSchema:
    """Order schema for complex nested structures."""
    return ItemSchema(
        name="order",
        required_fields={
            "order_id", "customer_id", "status", "items", "totals.total"
        },
        optional_fields={
            "shipping.method", "shipping.address", "payment.method",
            "payment.status", "timestamps.created", "timestamps.updated"
        },
        field_types={
            "order_id": "string",
            "customer_id": "string",
            "status": "string",
            "totals.total": "number"
        }
    )


# Stage Fixtures
@pytest.fixture
def registration_stage(simple_and_gate: Gate, basic_user_schema: ItemSchema) -> Stage:
    """Registration stage for user onboarding."""
    return Stage(
        name="registration",
        gates=[simple_and_gate],
        schema=basic_user_schema
    )


@pytest.fixture
def profile_stage(complex_and_gate: Gate, complete_user_schema: ItemSchema) -> Stage:
    """Profile completion stage."""
    return Stage(
        name="profile_completion",
        gates=[complex_and_gate],
        schema=complete_user_schema
    )


@pytest.fixture
def verification_stage(verified_equals_lock: Lock) -> Stage:
    """Email verification stage."""
    verification_gate = Gate(
        name="email_verification",
        locks=[verified_equals_lock],
        logic=GateOperation.AND
    )

    return Stage(
        name="verification",
        gates=[verification_gate]
    )


@pytest.fixture
def order_processing_stage(status_enum_lock: Lock, order_schema: ItemSchema) -> Stage:
    """Order processing stage."""
    processing_gate = Gate(
        name="order_validation",
        locks=[status_enum_lock],
        logic=GateOperation.AND
    )

    return Stage(
        name="order_processing",
        gates=[processing_gate],
        schema=order_schema
    )


# Process Fixtures
@pytest.fixture
def simple_linear_process(
    registration_stage: Stage,
    verification_stage: Stage
) -> Process:
    """Simple linear process with two stages."""
    return Process(
        name="simple_onboarding",
        stages=[registration_stage, verification_stage],
        stage_order=["registration", "verification"]
    )


@pytest.fixture
def complex_user_process(
    registration_stage: Stage,
    profile_stage: Stage,
    verification_stage: Stage
) -> Process:
    """Complex user onboarding process with multiple stages."""
    return Process(
        name="user_onboarding",
        stages=[registration_stage, profile_stage, verification_stage],
        stage_order=["registration", "profile_completion", "verification"]
    )


@pytest.fixture
def order_fulfillment_process(order_processing_stage: Stage) -> Process:
    """Order fulfillment process for e-commerce testing."""
    # Create additional stages for order flow
    payment_lock = Lock(
        property_path="payment.status",
        lock_type=LockType.EQUALS,
        expected_value="completed"
    )
    payment_gate = Gate(
        name="payment_complete",
        locks=[payment_lock],
        logic=GateOperation.AND
    )
    payment_stage = Stage(
        name="payment",
        gates=[payment_gate]
    )

    shipping_lock = Lock(
        property_path="shipping.tracking_number",
        lock_type=LockType.EXISTS
    )
    shipping_gate = Gate(
        name="shipping_started",
        locks=[shipping_lock],
        logic=GateOperation.AND
    )
    shipping_stage = Stage(
        name="shipping",
        gates=[shipping_gate]
    )

    return Process(
        name="order_fulfillment",
        stages=[order_processing_stage, payment_stage, shipping_stage],
        stage_order=["order_processing", "payment", "shipping"]
    )


# Factory Fixtures for Dynamic Creation
@pytest.fixture
def element_factory():
    """Factory function for creating custom elements."""
    def _create_element(data: dict[str, Any]) -> Element:
        return create_element(data)
    return _create_element


@pytest.fixture
def lock_factory():
    """Factory function for creating custom locks."""
    def _create_lock(
        property_path: str,
        lock_type: LockType,
        expected_value: Any = None,
        validator_name: str | None = None
    ) -> Lock:
        return Lock(
            property_path=property_path,
            lock_type=lock_type,
            expected_value=expected_value,
            validator_name=validator_name
        )
    return _create_lock


@pytest.fixture
def gate_factory():
    """Factory function for creating custom gates."""
    def _create_gate(
        name: str,
        locks: list[Lock],
        logic: GateOperation = GateOperation.AND
    ) -> Gate:
        return Gate(name=name, locks=locks, logic=logic)
    return _create_gate


@pytest.fixture
def stage_factory():
    """Factory function for creating custom stages."""
    def _create_stage(
        name: str,
        gates: list[Gate],
        schema: ItemSchema | None = None
    ) -> Stage:
        return Stage(name=name, gates=gates, schema=schema)
    return _create_stage


@pytest.fixture
def process_factory():
    """Factory function for creating custom processes."""
    def _create_process(
        name: str,
        stages: list[Stage],
        stage_order: list[str] | None = None
    ) -> Process:
        return Process(
            name=name,
            stages=stages,
            stage_order=stage_order or [stage.name for stage in stages]
        )
    return _create_process
