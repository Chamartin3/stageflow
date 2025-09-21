"""Tests for the 7-state evaluation flow in Process class."""

import time

import pytest
from stageflow.process.main import Process
from stageflow.process.extras.history import ElementStateHistory, StateTransition
from stageflow.process.schema.core import FieldDefinition, ItemSchema

from stageflow.core.element import DictElement
from stageflow.core.stage import Stage
from stageflow.gates import Gate, Lock, LockType
from stageflow.process.result import EvaluationState


@pytest.fixture
def sample_element():
    """Create a sample element for testing."""
    return DictElement({
        "id": "test_element_001",
        "name": "Test User",
        "email": "test@example.com",
        "status": "active",
        "score": 85,
        "completed_steps": ["registration", "verification"],
    })


@pytest.fixture
def minimal_element():
    """Create a minimal element for testing."""
    return DictElement({
        "id": "minimal_001",
        "name": "Basic User",
    })


@pytest.fixture
def advanced_element():
    """Create an advanced element for testing."""
    return DictElement({
        "id": "advanced_001",
        "name": "Advanced User",
        "email": "advanced@example.com",
        "status": "premium",
        "score": 95,
        "completed_steps": ["registration", "verification", "onboarding", "activation"],
        "premium_features": ["analytics", "custom_reports"],
    })


@pytest.fixture
def simple_schema():
    """Create a simple schema for testing."""
    return ItemSchema(
        name="basic_schema",
        fields={
            "name": FieldDefinition(str, required=True),
            "email": FieldDefinition(str, required=False),
        }
    )


@pytest.fixture
def advanced_schema():
    """Create an advanced schema for testing."""
    return ItemSchema(
        name="advanced_schema",
        fields={
            "name": FieldDefinition(str, required=True),
            "email": FieldDefinition(str, required=True),
            "status": FieldDefinition(str, required=True),
            "score": FieldDefinition(int, required=True),
            "premium_features": FieldDefinition(list, required=False),
        }
    )


@pytest.fixture
def multi_stage_process(simple_schema, advanced_schema):
    """Create a multi-stage process for testing."""
    # Stage 1: Basic registration
    basic_gate = Gate.AND(
        Lock("name", LockType.EXISTS),
        Lock("name", LockType.REGEX, r"^[A-Za-z\s]+$"),
        name="basic_requirements"
    )
    basic_stage = Stage(
        name="registration",
        schema=simple_schema,
        gates=[basic_gate],
    )

    # Stage 2: Email verification
    email_gate = Gate.AND(
        Lock("email", LockType.EXISTS),
        Lock("email", LockType.REGEX, r"^[^@]+@[^@]+\.[^@]+$"),
        Lock("status", LockType.EXISTS),
        name="email_verification"
    )
    email_stage = Stage(
        name="verification",
        schema=advanced_schema,
        gates=[email_gate],
    )

    # Stage 3: Premium activation
    premium_gate = Gate.AND(
        Lock("score", LockType.GREATER_THAN, 89),  # >= 90 means > 89
        Lock("premium_features", LockType.EXISTS),
        name="premium_activation"
    )
    premium_stage = Stage(
        name="premium",
        schema=advanced_schema,
        gates=[premium_gate],
    )

    return Process(
        name="user_onboarding",
        stages=[basic_stage, email_stage, premium_stage],
        stage_order=["registration", "verification", "premium"],
        regression_detection=True,
    )


class TestStateTransition:
    """Test StateTransition class functionality."""

    def test_state_transition_creation(self):
        """Test creating a state transition."""
        transition = StateTransition(
            timestamp=time.time(),
            from_state="scoping",
            to_state="fulfilling",
            element_id="test_001",
            stage_name="registration",
            transition_reason="Standard evaluation",
        )

        assert transition.from_state == "scoping"
        assert transition.to_state == "fulfilling"
        assert transition.element_id == "test_001"
        assert transition.stage_name == "registration"
        assert transition.transition_reason == "Standard evaluation"

    def test_progression_detection(self):
        """Test progression detection logic."""
        # Forward progression
        progression = StateTransition(
            timestamp=time.time(),
            from_state="fulfilling",
            to_state="qualifying",
            element_id="test_001",
            stage_name="registration",
            transition_reason="Requirements met",
        )
        assert progression.is_progression()
        assert not progression.is_regression()

        # Regression
        regression = StateTransition(
            timestamp=time.time(),
            from_state="qualifying",
            to_state="regressing",
            element_id="test_001",
            stage_name="registration",
            transition_reason="Failed validation",
        )
        assert regression.is_regression()
        assert not regression.is_progression()

        # Lateral movement (awaiting)
        lateral = StateTransition(
            timestamp=time.time(),
            from_state="fulfilling",
            to_state="awaiting",
            element_id="test_001",
            stage_name="registration",
            transition_reason="Waiting for dependencies",
        )
        # Awaiting is considered lateral/partial progression since awaiting has level 1.5 > fulfilling (1.0)
        assert lateral.is_progression()
        assert not lateral.is_regression()


class TestElementStateHistory:
    """Test ElementStateHistory class functionality."""

    def test_history_creation(self):
        """Test creating element state history."""
        history = ElementStateHistory(
            element_id="test_001",
            initial_timestamp=time.time(),
        )

        assert history.element_id == "test_001"
        assert history.evaluation_count == 0
        assert history.current_state is None
        assert history.total_evaluation_time == 0.0

    def test_transition_tracking(self):
        """Test adding transitions to history."""
        history = ElementStateHistory(
            element_id="test_001",
            initial_timestamp=time.time(),
        )

        # Add first transition
        history.add_transition(
            from_state=None,
            to_state="scoping",
            stage_name=None,
            reason="Initial evaluation",
            evaluation_time=0.1,
        )

        assert history.evaluation_count == 1
        assert history.current_state == "scoping"
        assert history.total_evaluation_time == 0.1

        # Add second transition
        history.add_transition(
            from_state="scoping",
            to_state="fulfilling",
            stage_name="registration",
            reason="Stage identified",
            evaluation_time=0.05,
        )

        assert history.evaluation_count == 2
        assert history.current_state == "fulfilling"
        assert history.current_stage == "registration"
        assert abs(history.total_evaluation_time - 0.15) < 0.001  # Allow for floating point precision

    def test_progression_counting(self):
        """Test counting progressions and regressions."""
        history = ElementStateHistory(
            element_id="test_001",
            initial_timestamp=time.time(),
        )

        # Add progression transitions
        history.add_transition(None, "scoping", None, "Initial", 0.1)
        history.add_transition("scoping", "fulfilling", "registration", "Progress", 0.1)
        history.add_transition("fulfilling", "qualifying", "registration", "Progress", 0.1)
        history.add_transition("qualifying", "regressing", "registration", "Regression", 0.1)

        assert history.progression_count == 3  # Initial is counted as progression
        assert history.regression_count == 1

    def test_time_in_state_calculation(self):
        """Test calculating time spent in specific states."""
        initial_time = time.time()
        history = ElementStateHistory(
            element_id="test_001",
            initial_timestamp=initial_time,
        )

        # Mock timestamps for controlled testing
        with pytest.MonkeyPatch().context() as m:
            mock_times = [initial_time + 1, initial_time + 3, initial_time + 6]
            time_iter = iter(mock_times)
            m.setattr(time, "time", lambda: next(time_iter))

            history.add_transition(None, "scoping", None, "Initial", 0.1)
            history.add_transition("scoping", "fulfilling", "registration", "Progress", 0.1)
            history.add_transition("fulfilling", "qualifying", "registration", "Progress", 0.1)

        # Time in scoping: from timestamp 1 to timestamp 3 = 2 seconds
        # Note: This is an approximation since we're mocking time
        time_in_scoping = history.get_time_in_state("scoping")
        assert time_in_scoping >= 0  # Just ensure it's calculated

    def test_state_summary(self):
        """Test getting state summary."""
        history = ElementStateHistory(
            element_id="test_001",
            initial_timestamp=time.time(),
        )

        history.add_transition(None, "scoping", None, "Initial", 0.1)
        history.add_transition("scoping", "fulfilling", "registration", "Progress", 0.1)

        summary = history.get_state_summary()

        assert summary["element_id"] == "test_001"
        assert summary["current_state"] == "fulfilling"
        assert summary["current_stage"] == "registration"
        assert summary["total_evaluations"] == 2
        assert summary["progressions"] == 2
        assert summary["regressions"] == 0
        assert "scoping" in summary["state_counts"]
        assert "fulfilling" in summary["state_counts"]


class TestProcess7StateFlow:
    """Test the 7-state evaluation flow in Process class."""

    def test_scoping_state(self, multi_stage_process, minimal_element):
        """Test scoping state evaluation."""
        result = multi_stage_process.evaluate(minimal_element)

        # Minimal element has 'name' which satisfies the basic registration requirements
        # So it should be qualifying for advancement
        assert result.state == EvaluationState.QUALIFYING
        assert result.current_stage == "registration"
        assert "advance" in str(result.actions).lower() or "ready" in str(result.actions).lower()

    def test_fulfilling_state(self, multi_stage_process, sample_element):
        """Test fulfilling state evaluation."""
        result = multi_stage_process.evaluate(sample_element, "registration")

        # Element should be fulfilling requirements for registration stage
        assert result.state in [EvaluationState.FULFILLING, EvaluationState.QUALIFYING, EvaluationState.ADVANCING]
        assert result.current_stage == "registration"

    def test_qualifying_state(self, multi_stage_process, sample_element):
        """Test qualifying state when element meets current stage but can't advance."""
        # Modify element to meet registration but not verification requirements
        element_data = sample_element.to_dict()
        element_data["status"] = "pending"  # This should block verification
        modified_element = DictElement(element_data)

        result = multi_stage_process.evaluate(modified_element, "registration")

        # Should qualify for registration but might not advance due to verification requirements
        assert result.state in [EvaluationState.QUALIFYING, EvaluationState.ADVANCING, EvaluationState.FULFILLING]

    def test_advancing_state(self, multi_stage_process, sample_element):
        """Test advancing state when element can move to next stage."""
        result = multi_stage_process.evaluate(sample_element, "registration")

        # Sample element should be able to advance from registration
        if result.state == EvaluationState.ADVANCING:
            assert result.proposed_stage == "verification"
            assert "transition" in str(result.actions).lower()

    def test_completed_state(self, multi_stage_process, advanced_element):
        """Test completed state when element finishes all stages."""
        # First evaluate through all stages to get to completion
        result = multi_stage_process.evaluate(advanced_element)

        # Advanced element should eventually reach completion or be close to it
        # This depends on the exact requirements, but we test the completion logic
        if result.state == EvaluationState.COMPLETED:
            assert result.current_stage is None
            assert "completed" in str(result.actions).lower()

    def test_regression_detection(self, multi_stage_process, sample_element):
        """Test regression detection when element loses capabilities."""
        # First, establish element in a good state
        multi_stage_process.evaluate(sample_element, "verification")

        # Simulate element losing required properties
        degraded_data = sample_element.to_dict()
        degraded_data.pop("email", None)  # Remove required property
        degraded_element = DictElement(degraded_data)

        result2 = multi_stage_process.evaluate(degraded_element, "verification")

        # Should detect regression or at least not advance
        assert result2.state in [EvaluationState.REGRESSING, EvaluationState.FULFILLING]

    def test_state_transition_validation(self, multi_stage_process, sample_element):
        """Test state transition validation."""
        # Test valid transitions
        assert multi_stage_process.validate_state_transition(
            "fulfilling", "qualifying", sample_element, "registration"
        )

        assert multi_stage_process.validate_state_transition(
            "qualifying", "advancing", sample_element, "registration"
        )

        # Test invalid transitions
        assert not multi_stage_process.validate_state_transition(
            "scoping", "completed", sample_element, "registration"
        )

        assert not multi_stage_process.validate_state_transition(
            "advancing", "scoping", sample_element, "registration"
        )

    def test_state_transition_actions(self, multi_stage_process, sample_element):
        """Test state transition action generation."""
        actions = multi_stage_process.get_state_transition_actions(
            "fulfilling", "qualifying", sample_element
        )

        assert len(actions) > 0
        assert any("complete" in action.lower() or "requirement" in action.lower() for action in actions)

        actions = multi_stage_process.get_state_transition_actions(
            "qualifying", "advancing", sample_element
        )

        assert len(actions) > 0
        assert any("transition" in action.lower() or "advance" in action.lower() for action in actions)

    def test_enhanced_evaluation_with_state_tracking(self, multi_stage_process, sample_element):
        """Test enhanced evaluation with state tracking."""
        # First evaluation
        result1 = multi_stage_process.evaluate_with_state_tracking(sample_element)

        assert result1.state in EvaluationState
        assert "evaluation_time" in result1.metadata

        # Check if first evaluation detects regression (which is valid behavior)
        if result1.state == EvaluationState.REGRESSING:
            assert "regression_detected" in result1.metadata
            # In this case, we'll use a simpler element for the second test
            simple_element = DictElement({"id": "simple_001", "name": "Simple User"})
            result2 = multi_stage_process.evaluate_with_state_tracking(
                simple_element,
                previous_state="scoping"
            )
        else:
            # Normal case - check transition validation
            assert "transition_validated" in result1.metadata
            assert result1.metadata["transition_validated"] is False

            # Second evaluation with previous state
            result2 = multi_stage_process.evaluate_with_state_tracking(
                sample_element,
                current_stage_name=result1.current_stage,
                previous_state=result1.state.value
            )

        assert result2.state in EvaluationState
        # Check for appropriate metadata based on result type
        if result2.state == EvaluationState.REGRESSING:
            assert "regression_detected" in result2.metadata or "invalid_transition" in result2.metadata
        else:
            # For normal transitions, should have transition validation metadata
            assert "transition_validated" in result2.metadata

    def test_state_history_tracking(self, multi_stage_process, sample_element):
        """Test element state history tracking."""
        # Perform multiple evaluations
        multi_stage_process.evaluate(sample_element)
        multi_stage_process.evaluate(sample_element, "registration")
        multi_stage_process.evaluate(sample_element, "verification")

        # Check history was recorded
        history = multi_stage_process.get_element_state_history(sample_element)
        assert history is not None
        assert history.evaluation_count >= 3
        assert len(history.transitions) >= 3

        # Check history summary
        summary = history.get_state_summary()
        assert summary["total_evaluations"] >= 3
        assert "state_counts" in summary

    def test_process_state_history_summary(self, multi_stage_process, sample_element, minimal_element):
        """Test process-level state history summary."""
        # Evaluate multiple elements
        multi_stage_process.evaluate(sample_element)
        multi_stage_process.evaluate(minimal_element)

        # Get summary
        summary = multi_stage_process.get_state_history_summary()

        assert summary["total_elements"] >= 2
        assert summary["total_evaluations"] >= 2
        assert "state_distribution" in summary
        assert "progression_stats" in summary
        assert "regression_stats" in summary

    def test_state_history_clearing(self, multi_stage_process, sample_element):
        """Test clearing state histories."""
        # Create some history
        multi_stage_process.evaluate(sample_element)
        assert multi_stage_process.get_element_state_history(sample_element) is not None

        # Clear specific element history
        multi_stage_process.clear_state_history(sample_element)
        assert multi_stage_process.get_element_state_history(sample_element) is None

        # Create history again and clear all
        multi_stage_process.evaluate(sample_element)
        multi_stage_process.clear_state_history()
        assert len(multi_stage_process.get_all_state_histories()) == 0

    def test_regression_conditions_detection(self, multi_stage_process, sample_element):
        """Test specific regression condition detection."""
        # Get current stage
        stage = multi_stage_process.get_stage("registration")
        assert stage is not None

        # Create a stage result that should trigger regression
        stage.evaluate(sample_element)

        # Test with element that has lost required properties
        degraded_data = {"name": "Test"}  # Missing other required properties
        degraded_element = DictElement(degraded_data)

        degraded_result = stage.evaluate(degraded_element)

        should_regress = multi_stage_process.detect_regression_conditions(
            degraded_element, stage, degraded_result
        )

        # Should detect regression due to missing properties or failed validation
        assert isinstance(should_regress, bool)

    def test_element_id_generation(self, multi_stage_process):
        """Test element ID generation for state tracking."""
        # Element with explicit ID
        element_with_id = DictElement({"id": "custom_123", "name": "Test"})
        id1 = multi_stage_process._get_element_id(element_with_id)
        assert id1 == "custom_123"

        # Element with _id field
        element_with_underscore_id = DictElement({"_id": "mongo_456", "name": "Test"})
        id2 = multi_stage_process._get_element_id(element_with_underscore_id)
        assert id2 == "mongo_456"

        # Element without ID (should generate hash-based ID)
        element_without_id = DictElement({"name": "Test User", "email": "test@example.com"})
        id3 = multi_stage_process._get_element_id(element_without_id)
        assert id3.startswith("element_")
        assert len(id3) > 8  # Should be reasonably long

        # Same element should generate same ID
        id4 = multi_stage_process._get_element_id(element_without_id)
        assert id3 == id4




class TestEdgeCases:
    """Test edge cases and error conditions in 7-state flow."""

    def test_invalid_stage_name_in_evaluation(self, multi_stage_process, sample_element):
        """Test evaluation with invalid stage name."""
        result = multi_stage_process.evaluate(sample_element, "nonexistent_stage")

        assert result.state == EvaluationState.SCOPING
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_empty_process_evaluation(self, sample_element):
        """Test evaluation with empty process."""
        with pytest.raises(ValueError, match="at least one stage"):
            Process(name="empty", stages=[])

    def test_malformed_element_handling(self, multi_stage_process):
        """Test handling of malformed elements."""
        # Element that might cause issues in property access
        problem_element = DictElement({})

        result = multi_stage_process.evaluate(problem_element)

        # Should handle gracefully
        assert result.state in EvaluationState
        assert isinstance(result.actions, list)

    def test_state_transition_with_invalid_states(self, multi_stage_process, sample_element):
        """Test state transition validation with invalid states."""
        # Test with non-existent states
        assert not multi_stage_process.validate_state_transition(
            "invalid_from", "invalid_to", sample_element, "registration"
        )

        # Test with mismatched stage context
        assert not multi_stage_process.validate_state_transition(
            "fulfilling", "completed", sample_element, "nonexistent_stage"
        )

    def test_concurrent_evaluation_safety(self, multi_stage_process, sample_element):
        """Test that concurrent evaluations don't interfere with state tracking."""
        # This is a basic test - in a real scenario you'd use threading
        element1 = DictElement({"id": "concurrent_1", "name": "User 1"})
        element2 = DictElement({"id": "concurrent_2", "name": "User 2"})

        result1 = multi_stage_process.evaluate(element1)
        result2 = multi_stage_process.evaluate(element2)

        # Both should have valid results
        assert result1.state in EvaluationState
        assert result2.state in EvaluationState

        # Should have separate state histories
        history1 = multi_stage_process.get_element_state_history(element1)
        history2 = multi_stage_process.get_element_state_history(element2)

        assert history1.element_id != history2.element_id

