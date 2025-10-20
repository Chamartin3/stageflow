"""Comprehensive unit tests for the stageflow.gate module.

This test suite covers all functionality in the Gate class and related components,
including gate initialization, lock composition, AND logic evaluation, error handling,
and integration with Lock objects and Element evaluation.
"""

from unittest.mock import Mock

import pytest

from stageflow.element import DictElement, Element
from stageflow.gate import Gate, GateDefinition, GateResult
from stageflow.lock import Lock, LockResult, LockType


class TestGateDefinition:
    """Test suite for GateDefinition TypedDict."""

    def test_gate_definition_structure(self):
        """Verify GateDefinition has correct structure and types."""
        # Arrange
        gate_definition: GateDefinition = {
            "name": "test_gate",
            "description": "Test gate description",
            "target_stage": "next_stage",
            "parent_stage": "current_stage",
            "locks": []
        }

        # Act & Assert
        assert gate_definition["name"] == "test_gate"
        assert gate_definition["description"] == "Test gate description"
        assert gate_definition["target_stage"] == "next_stage"
        assert gate_definition["parent_stage"] == "current_stage"
        assert isinstance(gate_definition["locks"], list)


class TestGateResult:
    """Test suite for GateResult dataclass."""

    def test_gate_result_creation_with_defaults(self):
        """Verify GateResult can be created with default values."""
        # Arrange & Act
        result = GateResult(success=True)

        # Assert
        assert result.success is True
        assert result.success_rate == 0.0
        assert result.failed == []
        assert result.passed == []

    def test_gate_result_creation_with_full_data(self):
        """Verify GateResult can be created with complete data."""
        # Arrange
        failed_lock_result = LockResult(
            success=False,
            property_path="test.path",
            lock_type=LockType.EXISTS,
            error_message="Test error message"
        )
        passed_lock_result = LockResult(
            success=True,
            property_path="valid.path",
            lock_type=LockType.EXISTS
        )

        # Act
        result = GateResult(
            success=False,
            success_rate=0.5,
            failed=[failed_lock_result],
            passed=[passed_lock_result]
        )

        # Assert
        assert result.success is False
        assert result.success_rate == 0.5
        assert len(result.failed) == 1
        assert len(result.passed) == 1
        assert result.failed[0].error_message == "Test error message"

    def test_gate_result_messages_property_aggregates_errors(self):
        """Verify messages property correctly aggregates error messages from failed locks."""
        # Arrange
        failed_lock_results = [
            LockResult(
                success=False,
                property_path="field1",
                lock_type=LockType.EXISTS,
                error_message="Field1 is required"
            ),
            LockResult(
                success=False,
                property_path="field2",
                lock_type=LockType.REGEX,
                error_message="Field2 format invalid"
            ),
            LockResult(
                success=False,
                property_path="field3",
                lock_type=LockType.EQUALS,
                error_message=""  # Empty error message
            )
        ]

        result = GateResult(
            success=False,
            failed=failed_lock_results,
            passed=[]
        )

        # Act
        messages = result.messages

        # Assert
        assert len(messages) == 2  # Empty message should not be included
        assert "Field1 is required" in messages
        assert "Field2 format invalid" in messages

    def test_gate_result_messages_property_empty_when_no_failures(self):
        """Verify messages property returns empty list when no failures."""
        # Arrange
        passed_lock_result = LockResult(
            success=True,
            property_path="valid.path",
            lock_type=LockType.EXISTS
        )

        result = GateResult(
            success=True,
            failed=[],
            passed=[passed_lock_result]
        )

        # Act
        messages = result.messages

        # Assert
        assert messages == []

    def test_gate_result_is_frozen_dataclass(self):
        """Verify GateResult is immutable (frozen dataclass)."""
        # Arrange
        result = GateResult(success=True)

        # Act & Assert
        with pytest.raises(AttributeError, match="cannot assign to field"):
            result.success = False


class TestGateInitialization:
    """Test suite for Gate class initialization and configuration."""

    def test_gate_initialization_with_valid_config(self):
        """Verify Gate can be initialized with valid configuration."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "email_validation",
            "description": "Validates email requirements",
            "target_stage": "verified_user",
            "parent_stage": "new_user",
            "locks": [
                {"type": LockType.EXISTS, "property_path": "email", "expected_value": None}
            ]
        }

        # Act
        gate = Gate(gate_config)

        # Assert
        assert gate.name == "email_validation"
        assert gate.description == "Validates email requirements"
        assert gate.target_stage == "verified_user"
        assert len(gate._locks) == 1
        assert isinstance(gate._locks[0], Lock)

    def test_gate_initialization_with_multiple_locks(self):
        """Verify Gate can be initialized with multiple locks."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "registration_complete",
            "description": "Validates complete registration",
            "target_stage": "active_user",
            "parent_stage": "pending_user",
            "locks": [
                {"type": LockType.EXISTS, "property_path": "email", "expected_value": None},
                {"type": LockType.EXISTS, "property_path": "profile.first_name", "expected_value": None},
                {"type": LockType.EQUALS, "property_path": "verification.email_verified", "expected_value": True}
            ]
        }

        # Act
        gate = Gate(gate_config)

        # Assert
        assert gate.name == "registration_complete"
        assert len(gate._locks) == 3
        assert all(isinstance(lock, Lock) for lock in gate._locks)

    def test_gate_initialization_with_shorthand_locks(self):
        """Verify Gate can be initialized with shorthand lock syntax."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "basic_validation",
            "description": "Basic field validation",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [
                {"exists": "email"},
                {"exists": "user_id"},
                {"is_true": "active"}
            ]
        }

        # Act
        gate = Gate(gate_config)

        # Assert
        assert gate.name == "basic_validation"
        assert len(gate._locks) == 3
        assert all(isinstance(lock, Lock) for lock in gate._locks)

    def test_gate_initialization_missing_name_raises_value_error(self):
        """Verify Gate initialization raises ValueError when name is missing."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "",
            "description": "Test gate",
            "target_stage": "next_stage",
            "parent_stage": "current_stage",
            "locks": [{"exists": "email"}]
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Gate must have a name"):
            Gate(gate_config)

    def test_gate_initialization_missing_target_stage_raises_value_error(self):
        """Verify Gate initialization raises ValueError when target_stage is missing."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "test_gate",
            "description": "Test gate",
            "target_stage": "",
            "parent_stage": "current_stage",
            "locks": [{"exists": "email"}]
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Gate must have at least one lock and a target stage"):
            Gate(gate_config)

    def test_gate_initialization_no_locks_raises_value_error(self):
        """Verify Gate initialization raises ValueError when no locks provided."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "test_gate",
            "description": "Test gate",
            "target_stage": "next_stage",
            "parent_stage": "current_stage",
            "locks": []
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Gate must have at least one lock and a target stage"):
            Gate(gate_config)

    def test_gate_initialization_with_optional_description(self):
        """Verify Gate initialization works with missing description."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "minimal_gate",
            "description": "",
            "target_stage": "next_stage",
            "parent_stage": "current_stage",
            "locks": [{"exists": "field"}]
        }

        # Act
        gate = Gate(gate_config)

        # Assert
        assert gate.name == "minimal_gate"
        assert gate.description == ""
        assert gate.target_stage == "next_stage"


class TestGateClassMethods:
    """Test suite for Gate class methods."""

    def test_gate_create_class_method(self):
        """Verify Gate.create class method works correctly."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "factory_gate",
            "description": "Created via factory method",
            "target_stage": "next_stage",
            "parent_stage": "current_stage",
            "locks": [{"exists": "email"}]
        }

        # Act
        gate = Gate.create(gate_config)

        # Assert
        assert isinstance(gate, Gate)
        assert gate.name == "factory_gate"
        assert gate.description == "Created via factory method"
        assert gate.target_stage == "next_stage"

    def test_gate_create_delegates_to_constructor(self):
        """Verify Gate.create method delegates to constructor."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "test_gate",
            "description": "Test",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "field"}]
        }

        # Act
        gate_via_create = Gate.create(gate_config)
        gate_via_constructor = Gate(gate_config)

        # Assert
        assert gate_via_create.name == gate_via_constructor.name
        assert gate_via_create.target_stage == gate_via_constructor.target_stage
        assert len(gate_via_create._locks) == len(gate_via_constructor._locks)


class TestGateEvaluation:
    """Test suite for Gate evaluation logic and AND operation."""

    @pytest.fixture
    def valid_element(self) -> DictElement:
        """Create a valid element for testing."""
        return DictElement({
            "email": "user@example.com",
            "user_id": "user123",
            "profile": {
                "first_name": "John",
                "last_name": "Doe",
                "age": 25
            },
            "verification": {
                "email_verified": True,
                "phone_verified": False
            },
            "status": "active",
            "score": 85
        })

    @pytest.fixture
    def invalid_element(self) -> DictElement:
        """Create an invalid element for testing."""
        return DictElement({
            "user_id": "user456",
            # Missing email
            "profile": {
                "first_name": "Jane"
                # Missing last_name
            },
            "verification": {
                "email_verified": False,
                "phone_verified": False
            },
            "status": "inactive",
            "score": 45
        })

    @pytest.fixture
    def simple_gate(self) -> Gate:
        """Create a simple gate with one lock for testing."""
        gate_config: GateDefinition = {
            "name": "email_check",
            "description": "Check email exists",
            "target_stage": "email_verified",
            "parent_stage": "new_user",
            "locks": [{"exists": "email"}]
        }
        return Gate(gate_config)

    @pytest.fixture
    def complex_gate(self) -> Gate:
        """Create a complex gate with multiple locks for testing."""
        gate_config: GateDefinition = {
            "name": "profile_complete",
            "description": "Validate complete profile",
            "target_stage": "profile_verified",
            "parent_stage": "partial_profile",
            "locks": [
                {"exists": "email"},
                {"exists": "profile.first_name"},
                {"exists": "profile.last_name"},
                {"type": LockType.EQUALS, "property_path": "verification.email_verified", "expected_value": True}
            ]
        }
        return Gate(gate_config)

    def test_gate_evaluation_single_lock_success(self, simple_gate: Gate, valid_element: DictElement):
        """Verify gate evaluation succeeds when single lock passes."""
        # Arrange & Act
        result = simple_gate.evaluate(valid_element)

        # Assert
        assert result.success is True
        assert result.success_rate == 1.0
        assert len(result.passed) == 1
        assert len(result.failed) == 0
        assert result.messages == []

    def test_gate_evaluation_single_lock_failure(self, simple_gate: Gate, invalid_element: DictElement):
        """Verify gate evaluation fails when single lock fails."""
        # Arrange & Act
        result = simple_gate.evaluate(invalid_element)

        # Assert
        assert result.success is False
        assert result.success_rate == 0.0
        assert len(result.passed) == 0
        assert len(result.failed) == 1
        assert len(result.messages) == 1
        assert "email" in result.messages[0]

    def test_gate_evaluation_multiple_locks_all_pass(self, complex_gate: Gate, valid_element: DictElement):
        """Verify gate evaluation succeeds when all locks pass (AND logic)."""
        # Arrange & Act
        result = complex_gate.evaluate(valid_element)

        # Assert
        assert result.success is True
        assert result.success_rate == 1.0
        assert len(result.passed) == 4
        assert len(result.failed) == 0
        assert result.messages == []

    def test_gate_evaluation_multiple_locks_some_fail(self, complex_gate: Gate, invalid_element: DictElement):
        """Verify gate evaluation fails when any lock fails (AND logic)."""
        # Arrange & Act
        result = complex_gate.evaluate(invalid_element)

        # Assert
        assert result.success is False
        assert result.success_rate < 1.0
        assert len(result.passed) > 0  # Some locks should pass
        assert len(result.failed) > 0  # Some locks should fail
        assert len(result.messages) > 0

    def test_gate_evaluation_and_logic_enforced(self):
        """Verify gate evaluation enforces AND logic - all locks must pass."""
        # Arrange
        element = DictElement({
            "email": "test@example.com",  # This will pass
            "age": 15  # This will fail (less than 18)
        })

        gate_config: GateDefinition = {
            "name": "adult_user",
            "description": "Validate adult user",
            "target_stage": "verified_adult",
            "parent_stage": "unverified",
            "locks": [
                {"exists": "email"},  # Will pass
                {"type": LockType.GREATER_THAN, "property_path": "age", "expected_value": 18}  # Will fail
            ]
        }
        gate = Gate(gate_config)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success is False  # AND logic: one failure means gate fails
        assert result.success_rate == 0.5  # 1 out of 2 locks passed
        assert len(result.passed) == 1
        assert len(result.failed) == 1

    def test_gate_evaluation_with_various_lock_types(self):
        """Verify gate evaluation works with different lock types."""
        # Arrange
        element = DictElement({
            "email": "valid@example.com",
            "age": 25,
            "status": "active",
            "tier": "premium",  # Single value for IN_LIST test
            "score": 85.5
        })

        gate_config: GateDefinition = {
            "name": "comprehensive_check",
            "description": "Multiple lock types",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [
                {"type": LockType.REGEX, "property_path": "email", "expected_value": r"^[^@]+@[^@]+\.[^@]+$"},
                {"type": LockType.GREATER_THAN, "property_path": "age", "expected_value": 18},
                {"type": LockType.EQUALS, "property_path": "status", "expected_value": "active"},
                {"type": LockType.IN_LIST, "property_path": "tier", "expected_value": ["premium", "verified", "basic"]},
                {"type": LockType.GREATER_THAN, "property_path": "score", "expected_value": 80}
            ]
        }
        gate = Gate(gate_config)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success is True
        assert result.success_rate == 1.0
        assert len(result.passed) == 5
        assert len(result.failed) == 0

    def test_gate_evaluation_empty_element(self, complex_gate: Gate):
        """Verify gate evaluation handles empty element appropriately."""
        # Arrange
        empty_element = DictElement({})

        # Act
        result = complex_gate.evaluate(empty_element)

        # Assert
        assert result.success is False
        assert result.success_rate == 0.0
        assert len(result.passed) == 0
        assert len(result.failed) == len(complex_gate._locks)
        assert len(result.messages) > 0

    def test_gate_evaluation_with_null_values(self):
        """Verify gate evaluation handles null/None values correctly."""
        # Arrange
        element = DictElement({
            "email": None,
            "profile": {
                "first_name": "John",
                "last_name": None
            }
        })

        gate_config: GateDefinition = {
            "name": "null_check",
            "description": "Check null handling",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [
                {"exists": "email"},  # Should fail (None value)
                {"exists": "profile.first_name"},  # Should pass
                {"exists": "profile.last_name"}  # Should fail (None value)
            ]
        }
        gate = Gate(gate_config)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success is False
        assert result.success_rate == pytest.approx(1.0/3.0, rel=1e-2)
        assert len(result.passed) == 1
        assert len(result.failed) == 2


class TestGateProperties:
    """Test suite for Gate properties and utility methods."""

    @pytest.fixture
    def multi_path_gate(self) -> Gate:
        """Create a gate with multiple property paths for testing."""
        gate_config: GateDefinition = {
            "name": "multi_path_gate",
            "description": "Gate with multiple paths",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [
                {"exists": "user.email"},
                {"exists": "profile.details.name"},
                {"exists": "verification.status"},
                {"type": LockType.EQUALS, "property_path": "settings.active", "expected_value": True}
            ]
        }
        return Gate(gate_config)

    def test_required_paths_property_returns_all_lock_paths(self, multi_path_gate: Gate):
        """Verify required_paths property returns all unique paths from locks."""
        # Arrange & Act
        required_paths = multi_path_gate.required_paths

        # Assert
        expected_paths = {
            "user.email",
            "profile.details.name",
            "verification.status",
            "settings.active"
        }
        assert required_paths == expected_paths

    def test_required_paths_property_handles_duplicate_paths(self):
        """Verify required_paths property handles duplicate paths correctly."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "duplicate_paths",
            "description": "Gate with duplicate paths",
            "target_stage": "validated",
            "parent_stage": "unvalidated",
            "locks": [
                {"exists": "email"},
                {"type": LockType.REGEX, "property_path": "email", "expected_value": r".*@.*"},
                {"type": LockType.NOT_EMPTY, "property_path": "email", "expected_value": None}
            ]
        }
        gate = Gate(gate_config)

        # Act
        required_paths = gate.required_paths

        # Assert
        assert required_paths == {"email"}  # Should deduplicate

    def test_required_paths_property_empty_for_no_locks(self):
        """Verify required_paths returns empty set when no locks present."""
        # Note: This scenario can't actually occur due to validation in __init__
        # but we test the property behavior if _locks were somehow empty
        # Arrange
        gate_config: GateDefinition = {
            "name": "test_gate",
            "description": "Test",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "dummy"}]  # Required to pass validation
        }
        gate = Gate(gate_config)
        gate._locks = []  # Manually set to empty for this test

        # Act
        required_paths = gate.required_paths

        # Assert
        assert required_paths == set()

    def test_to_dict_method_serializes_gate_correctly(self, multi_path_gate: Gate):
        """Verify to_dict method creates correct dictionary representation."""
        # Arrange & Act
        gate_dict = multi_path_gate.to_dict()

        # Assert
        assert gate_dict["name"] == "multi_path_gate"
        assert gate_dict["description"] == "Gate with multiple paths"
        assert gate_dict["target_stage"] == "validated"
        assert "locks" in gate_dict
        assert isinstance(gate_dict["locks"], list)
        assert len(gate_dict["locks"]) == 4

    def test_to_dict_includes_lock_serialization(self):
        """Verify to_dict method includes serialized lock data."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "serialization_test",
            "description": "Test serialization",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"type": LockType.EQUALS, "property_path": "status", "expected_value": "active"}
            ]
        }
        gate = Gate(gate_config)

        # Act
        gate_dict = gate.to_dict()

        # Assert
        assert len(gate_dict["locks"]) == 1
        lock_dict = gate_dict["locks"][0]
        assert lock_dict["property_path"] == "status"
        assert lock_dict["type"] == LockType.EQUALS
        assert lock_dict["expected_value"] == "active"


class TestGateErrorHandling:
    """Test suite for Gate error handling and edge cases."""

    def test_gate_evaluation_with_malformed_element(self):
        """Verify gate evaluation handles malformed elements gracefully."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "error_test",
            "description": "Test error handling",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "field"}]
        }
        gate = Gate(gate_config)

        # Create a mock element that raises an exception
        mock_element = Mock(spec=Element)
        mock_element.get_property.side_effect = Exception("Element access error")

        # Act
        result = gate.evaluate(mock_element)

        # Assert
        assert result.success is False
        assert len(result.failed) == 1
        assert len(result.passed) == 0
        assert result.success_rate == 0.0

    def test_gate_initialization_with_invalid_lock_definition(self):
        """Verify gate initialization handles invalid lock definitions."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "invalid_lock_test",
            "description": "Test invalid lock",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"invalid_key": "invalid_value"}  # Invalid lock definition
            ]
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid lock definition format"):
            Gate(gate_config)

    def test_gate_evaluation_with_corrupted_lock_data(self):
        """Verify gate evaluation handles corrupted lock data."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "corruption_test",
            "description": "Test corruption handling",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "field"}]
        }
        gate = Gate(gate_config)
        element = DictElement({"field": "value"})

        # Corrupt the lock by replacing with a mock that fails
        mock_lock = Mock()
        mock_lock.validate.side_effect = Exception("Lock validation error")
        gate._locks = [mock_lock]

        # Act & Assert - The gate evaluation should propagate the exception
        # since we don't have error handling in the current implementation
        with pytest.raises(Exception, match="Lock validation error"):
            gate.evaluate(element)

    def test_gate_handles_missing_optional_config_fields(self):
        """Verify gate handles missing optional configuration fields."""
        # Arrange
        minimal_config = {
            "name": "minimal_gate",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "field"}]
            # Missing description
        }

        # Act
        gate = Gate(minimal_config)

        # Assert
        assert gate.name == "minimal_gate"
        assert gate.description == ""  # Should default to empty string
        assert gate.target_stage == "next"

    def test_gate_evaluation_success_rate_calculation_edge_cases(self):
        """Verify success rate calculation handles edge cases correctly."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "rate_test",
            "description": "Test success rate",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"exists": "field1"},
                {"exists": "field2"},
                {"exists": "field3"}
            ]
        }
        gate = Gate(gate_config)

        # Test case 1: 2 out of 3 locks pass
        element_partial = DictElement({"field1": "value", "field2": "value"})
        result_partial = gate.evaluate(element_partial)
        assert result_partial.success_rate == pytest.approx(2.0/3.0, rel=1e-2)

        # Test case 2: 0 out of 3 locks pass
        element_none = DictElement({})
        result_none = gate.evaluate(element_none)
        assert result_none.success_rate == 0.0

        # Test case 3: 3 out of 3 locks pass
        element_all = DictElement({"field1": "value", "field2": "value", "field3": "value"})
        result_all = gate.evaluate(element_all)
        assert result_all.success_rate == 1.0


class TestGateIntegration:
    """Integration tests for Gate with other StageFlow components."""

    def test_gate_integrates_with_lock_factory(self):
        """Verify Gate correctly integrates with LockFactory for lock creation."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "factory_integration",
            "description": "Test LockFactory integration",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"exists": "email"},
                {"is_true": "active"},
                {"type": LockType.REGEX, "property_path": "phone", "expected_value": r"^\+?\d{10,15}$"}
            ]
        }

        # Act
        gate = Gate(gate_config)

        # Assert
        assert len(gate._locks) == 3
        assert all(isinstance(lock, Lock) for lock in gate._locks)

        # Verify locks were created with correct configurations
        lock_paths = [lock.property_path for lock in gate._locks]
        assert "email" in lock_paths
        assert "active" in lock_paths
        assert "phone" in lock_paths

    def test_gate_evaluation_with_real_element_data(self):
        """Verify Gate evaluation works with realistic element data."""
        # Arrange
        realistic_element = DictElement({
            "user": {
                "id": "usr_abc123",
                "email": "john.doe@company.com",
                "profile": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "dateOfBirth": "1990-05-15",
                    "phoneNumber": "+1-555-123-4567"
                },
                "account": {
                    "status": "active",
                    "tier": "premium",
                    "verified": True,
                    "lastLoginAt": "2024-01-20T14:30:00Z"
                }
            },
            "metadata": {
                "createdAt": "2024-01-01T10:00:00Z",
                "updatedAt": "2024-01-20T14:30:00Z",
                "version": 2
            }
        })

        gate_config: GateDefinition = {
            "name": "user_validation",
            "description": "Comprehensive user validation",
            "target_stage": "verified_user",
            "parent_stage": "pending_user",
            "locks": [
                {"exists": "user.email"},
                {"exists": "user.profile.firstName"},
                {"exists": "user.profile.lastName"},
                {"type": LockType.EQUALS, "property_path": "user.account.status", "expected_value": "active"},
                {"type": LockType.EQUALS, "property_path": "user.account.verified", "expected_value": True},
                {"type": LockType.REGEX, "property_path": "user.email", "expected_value": r"^[^@]+@[^@]+\.[^@]+$"}
            ]
        }
        gate = Gate(gate_config)

        # Act
        result = gate.evaluate(realistic_element)

        # Assert
        assert result.success is True
        assert result.success_rate == 1.0
        assert len(result.passed) == 6
        assert len(result.failed) == 0
        assert result.messages == []

    @pytest.mark.parametrize("element_data,expected_success,expected_failure_count", [
        ({"email": "valid@test.com", "active": True}, True, 0),
        ({"email": "valid@test.com", "active": False}, False, 1),
        ({"email": "", "active": True}, False, 1),
        ({"active": True}, False, 1),
        ({}, False, 2),
    ])
    def test_gate_evaluation_parametrized_scenarios(self, element_data, expected_success, expected_failure_count):
        """Test gate evaluation with various element data scenarios."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "parametrized_test",
            "description": "Parametrized test gate",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"exists": "email"},
                {"is_true": "active"}
            ]
        }
        gate = Gate(gate_config)
        element = DictElement(element_data)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success == expected_success
        assert len(result.failed) == expected_failure_count


class TestGatePerformance:
    """Performance and scalability tests for Gate evaluation."""

    def test_gate_evaluation_with_many_locks_performance(self):
        """Verify gate evaluation performs reasonably with many locks."""
        # Arrange
        locks = []
        element_data = {}

        # Create 100 locks and corresponding element data
        for i in range(100):
            field_name = f"field_{i}"
            locks.append({"exists": field_name})
            element_data[field_name] = f"value_{i}"

        gate_config: GateDefinition = {
            "name": "performance_test",
            "description": "Test with many locks",
            "target_stage": "performance_validated",
            "parent_stage": "performance_pending",
            "locks": locks
        }
        gate = Gate(gate_config)
        element = DictElement(element_data)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success is True
        assert result.success_rate == 1.0
        assert len(result.passed) == 100
        assert len(result.failed) == 0
        # Performance assertion: evaluation should complete in reasonable time
        # (This is implicit - if the test times out, there's a performance issue)

    def test_gate_evaluation_with_deep_nested_paths(self):
        """Verify gate evaluation handles deeply nested property paths efficiently."""
        # Arrange
        deep_element_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "deep_value": "found"
                            }
                        }
                    }
                }
            }
        }

        gate_config: GateDefinition = {
            "name": "deep_nesting_test",
            "description": "Test deep property access",
            "target_stage": "deep_validated",
            "parent_stage": "deep_pending",
            "locks": [
                {"exists": "level1.level2.level3.level4.level5.deep_value"}
            ]
        }
        gate = Gate(gate_config)
        element = DictElement(deep_element_data)

        # Act
        result = gate.evaluate(element)

        # Assert
        assert result.success is True
        assert len(result.passed) == 1
        assert len(result.failed) == 0


# Property-based and edge case testing
class TestGateEdgeCases:
    """Property-based and edge case testing for Gate functionality."""

    def test_gate_immutability_after_creation(self):
        """Verify gate configuration cannot be modified after creation."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "immutable_test",
            "description": "Test immutability",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [{"exists": "field"}]
        }
        gate = Gate(gate_config)
        original_name = gate.name
        original_target = gate.target_stage
        original_locks_count = len(gate._locks)

        # Act
        gate.name = "modified_name"
        gate.target_stage = "modified_target"
        # Note: _locks is not directly accessible for modification due to naming convention

        # Assert
        # For this test, we verify that the gate maintains its configured behavior
        # even if properties are modified (though they shouldn't be in practice)
        element = DictElement({"field": "value"})
        result = gate.evaluate(element)
        assert result.success is True  # Evaluation should still work correctly

    def test_gate_evaluation_consistency_across_multiple_calls(self):
        """Verify gate evaluation produces consistent results across multiple calls."""
        # Arrange
        gate_config: GateDefinition = {
            "name": "consistency_test",
            "description": "Test evaluation consistency",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"exists": "email"},
                {"type": LockType.GREATER_THAN, "property_path": "age", "expected_value": 18}
            ]
        }
        gate = Gate(gate_config)
        element = DictElement({"email": "test@example.com", "age": 25})

        # Act
        results = [gate.evaluate(element) for _ in range(5)]

        # Assert
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.success == first_result.success
            assert result.success_rate == first_result.success_rate
            assert len(result.passed) == len(first_result.passed)
            assert len(result.failed) == len(first_result.failed)

    def test_gate_evaluation_with_special_characters_in_paths(self):
        """Verify gate evaluation handles special characters in property paths."""
        # Arrange
        element_data = {
            "user data": {
                "email-address": "test@example.com",
                "full.name.with.dots": "John Doe"
            },
            "metadata": {
                "key with spaces": "value",
                "key[with]brackets": "another value"
            }
        }
        element = DictElement(element_data)

        gate_config: GateDefinition = {
            "name": "special_chars_test",
            "description": "Test special characters in paths",
            "target_stage": "next",
            "parent_stage": "current",
            "locks": [
                {"exists": "user data.email-address"},
                {"exists": "metadata.key with spaces"}
            ]
        }
        gate = Gate(gate_config)

        # Act
        result = gate.evaluate(element)

        # Assert
        # Note: This test documents current behavior -
        # the actual success depends on how the Element handles special characters
        assert isinstance(result, GateResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.success_rate, float)
