"""Pytest fixtures for visualization module tests.

This module provides shared fixtures for testing the stageflow visualization
components, including mock processes, stages, gates, and realistic test scenarios.
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import Mock

from stageflow.process import Process
from stageflow.stage import Stage
from stageflow.gate import Gate
from stageflow.lock import Lock, LockType


@pytest.fixture
def simple_mock_process() -> Mock:
    """Create a simple mock process for basic visualization testing."""
    process = Mock(spec=Process)
    process.name = "simple_process"
    process.get_sorted_stages = Mock(return_value=["start", "middle", "end"])

    # Create mock stages
    start_stage = Mock()
    start_stage.name = "Start Stage"
    start_stage.gates = []

    middle_stage = Mock()
    middle_stage.name = "Middle Stage"
    middle_stage.gates = [Mock()]
    middle_stage.gates[0].name = "transition_gate"

    end_stage = Mock()
    end_stage.name = "End Stage"
    end_stage.gates = []

    # Configure stage lookup
    def get_stage_side_effect(stage_name):
        return {
            "start": start_stage,
            "middle": middle_stage,
            "end": end_stage
        }.get(stage_name)

    process.get_stage = Mock(side_effect=get_stage_side_effect)
    return process


@pytest.fixture
def complex_mock_process() -> Mock:
    """Create a complex mock process with gates and locks for detailed testing."""
    process = Mock(spec=Process)
    process.name = "complex_workflow"
    process.get_sorted_stages = Mock(return_value=["registration", "validation", "approval", "completion"])

    # Registration stage
    registration_stage = Mock()
    registration_stage.name = "User Registration"
    registration_stage.gates = []
    registration_stage.schema = {"required": ["email", "password"]}

    # Validation stage with gates
    validation_stage = Mock()
    validation_stage.name = "Data Validation"

    # Create validation gate with locks
    validation_gate = Mock()
    validation_gate.name = "email_validation"

    # Create mock locks
    email_lock = Mock()
    email_lock.property = "email"
    email_lock.type = Mock()
    email_lock.type.value = "REGEX"
    email_lock.expected_value = r"^[^@]+@[^@]+\.[^@]+$"

    validation_gate.locks = [email_lock]
    validation_stage.gates = [validation_gate]

    # Approval stage
    approval_stage = Mock()
    approval_stage.name = "Manual Approval"
    approval_gate = Mock()
    approval_gate.name = "admin_approval"
    approval_gate.locks = []
    approval_stage.gates = [approval_gate]

    # Completion stage
    completion_stage = Mock()
    completion_stage.name = "Process Complete"
    completion_stage.gates = []

    # Configure stage lookup
    def get_stage_side_effect(stage_name):
        return {
            "registration": registration_stage,
            "validation": validation_stage,
            "approval": approval_stage,
            "completion": completion_stage
        }.get(stage_name)

    process.get_stage = Mock(side_effect=get_stage_side_effect)
    return process


@pytest.fixture
def mock_stage_with_gates() -> Mock:
    """Create a mock stage with multiple gates for stage detail testing."""
    stage = Mock()
    stage.name = "Multi-Gate Stage"

    # Create gates with different characteristics
    gate1 = Mock()
    gate1.name = "input_validation"

    # Mock locks for gate1
    lock1 = Mock()
    lock1.property = "user_id"
    lock1.type = Mock()
    lock1.type.value = "EXISTS"
    lock1.expected_value = None

    gate1.locks = [lock1]

    gate2 = Mock()
    gate2.name = "business_rules"

    # Mock locks for gate2
    lock2 = Mock()
    lock2.property = "age"
    lock2.type = Mock()
    lock2.type.value = "GREATER_THAN"
    lock2.expected_value = 18

    gate2.locks = [lock2]

    stage.gates = [gate1, gate2]
    return stage


@pytest.fixture
def mock_stage_without_gates() -> Mock:
    """Create a mock stage without gates for testing empty scenarios."""
    stage = Mock()
    stage.name = "Simple Stage"
    stage.gates = []
    return stage


@pytest.fixture
def mock_gates_list() -> List[Mock]:
    """Create a list of mock gates for flowchart testing."""
    gate1 = Mock()
    gate1.name = "first_gate"

    gate2 = Mock()
    gate2.name = "second_gate"

    gate3 = Mock()
    gate3.name = "final_gate"

    return [gate1, gate2, gate3]


@pytest.fixture
def empty_mock_process() -> Mock:
    """Create an empty mock process for edge case testing."""
    process = Mock(spec=Process)
    process.name = "empty_process"
    process.get_sorted_stages = Mock(return_value=[])
    process.get_stage = Mock(return_value=None)
    return process


@pytest.fixture
def realistic_ecommerce_process_config() -> Dict[str, Any]:
    """Create a realistic e-commerce process configuration for integration testing."""
    return {
        "name": "ecommerce_order_processing",
        "description": "Complete e-commerce order processing workflow",
        "stages": {
            "cart": {
                "name": "Shopping Cart",
                "expected_properties": {
                    "items": {"type": "list"},
                    "customer_id": {"type": "str"}
                },
                "gates": [{
                    "name": "cart_validated",
                    "target_stage": "checkout",
                    "locks": [
                        {"exists": "items"},
                        {"exists": "customer_id"}
                    ]
                }]
            },
            "checkout": {
                "name": "Checkout Process",
                "expected_properties": {
                    "billing_address": {"type": "dict"},
                    "shipping_address": {"type": "dict"},
                    "payment_method": {"type": "str"}
                },
                "gates": [{
                    "name": "checkout_complete",
                    "target_stage": "payment",
                    "locks": [
                        {"exists": "billing_address"},
                        {"exists": "shipping_address"},
                        {"exists": "payment_method"}
                    ]
                }]
            },
            "payment": {
                "name": "Payment Processing",
                "expected_properties": {
                    "payment_status": {"type": "str"},
                    "transaction_id": {"type": "str"}
                },
                "gates": [{
                    "name": "payment_successful",
                    "target_stage": "fulfillment",
                    "locks": [
                        {"type": "EQUALS", "property": "payment_status", "value": "completed"},
                        {"exists": "transaction_id"}
                    ]
                }]
            },
            "fulfillment": {
                "name": "Order Fulfillment",
                "expected_properties": {
                    "fulfillment_status": {"type": "str"},
                    "tracking_number": {"type": "str"}
                },
                "gates": [{
                    "name": "order_shipped",
                    "target_stage": "delivered",
                    "locks": [
                        {"type": "EQUALS", "property": "fulfillment_status", "value": "shipped"},
                        {"exists": "tracking_number"}
                    ]
                }]
            },
            "delivered": {
                "name": "Order Delivered",
                "expected_properties": {
                    "delivery_status": {"type": "str"},
                    "delivered_date": {"type": "str"}
                },
                "gates": [{
                    "name": "delivery_confirmed",
                    "target_stage": "completed",
                    "locks": [
                        {"type": "EQUALS", "property": "delivery_status", "value": "delivered"},
                        {"exists": "delivered_date"}
                    ]
                }]
            },
            "completed": {
                "name": "Order Completed",
                "gates": [],
                "is_final": True
            }
        },
        "initial_stage": "cart",
        "final_stage": "completed"
    }


@pytest.fixture
def mock_stage_with_components() -> Mock:
    """Create a mock stage with gate components for Graphviz testing."""
    stage = Mock()
    stage.name = "Component Test Stage"

    # Create gate with components
    gate = Mock()
    gate.name = "validation_gate"

    # Create components with locks
    component1 = Mock()
    component1.lock = Mock()
    component1.lock.property_path = "email"
    component1.lock.lock_type = Mock()
    component1.lock.lock_type.value = "REGEX"
    component1.lock.expected_value = r"^[^@]+@[^@]+\.[^@]+$"

    component2 = Mock()
    component2.lock = Mock()
    component2.lock.property_path = "age"
    component2.lock.lock_type = Mock()
    component2.lock.lock_type.value = "GREATER_THAN"
    component2.lock.expected_value = 18

    gate.components = [component1, component2]
    stage.gates = [gate]
    return stage


@pytest.fixture
def mock_user_onboarding_process() -> Mock:
    """Create a mock user onboarding process for realistic testing scenarios."""
    process = Mock(spec=Process)
    process.name = "user_onboarding"
    process.get_sorted_stages = Mock(return_value=["signup", "email_verification", "profile_setup", "activation"])

    # Signup stage
    signup_stage = Mock()
    signup_stage.name = "User Signup"
    signup_gate = Mock()
    signup_gate.name = "signup_complete"
    signup_gate.locks = [Mock()]  # Basic lock mock
    signup_stage.gates = [signup_gate]

    # Email verification stage
    email_stage = Mock()
    email_stage.name = "Email Verification"
    email_gate = Mock()
    email_gate.name = "email_verified"
    email_gate.locks = [Mock()]
    email_stage.gates = [email_gate]

    # Profile setup stage
    profile_stage = Mock()
    profile_stage.name = "Profile Setup"
    profile_gate = Mock()
    profile_gate.name = "profile_complete"
    profile_gate.locks = [Mock(), Mock()]  # Multiple locks
    profile_stage.gates = [profile_gate]

    # Activation stage
    activation_stage = Mock()
    activation_stage.name = "Account Activated"
    activation_stage.gates = []  # Final stage

    # Configure stage lookup
    def get_stage_side_effect(stage_name):
        return {
            "signup": signup_stage,
            "email_verification": email_stage,
            "profile_setup": profile_stage,
            "activation": activation_stage
        }.get(stage_name)

    process.get_stage = Mock(side_effect=get_stage_side_effect)
    return process


@pytest.fixture
def mock_process_with_edge_cases() -> Mock:
    """Create a mock process with edge cases for error handling testing."""
    process = Mock(spec=Process)
    process.name = "edge_case_process"
    process.get_sorted_stages = Mock(return_value=["normal_stage", "missing_stage", "malformed_stage"])

    # Normal stage
    normal_stage = Mock()
    normal_stage.name = "Normal Stage"
    normal_stage.gates = []

    # Malformed stage (missing name)
    malformed_stage = Mock()
    malformed_stage.gates = []
    # Intentionally not setting name to test error handling

    # Configure stage lookup with edge cases
    def get_stage_side_effect(stage_name):
        if stage_name == "normal_stage":
            return normal_stage
        elif stage_name == "missing_stage":
            return None  # Simulate missing stage
        elif stage_name == "malformed_stage":
            return malformed_stage
        return None

    process.get_stage = Mock(side_effect=get_stage_side_effect)
    return process


@pytest.fixture(params=["overview", "detailed", "full"])
def visualization_style(request) -> str:
    """Parametrized fixture for different visualization styles."""
    return request.param


@pytest.fixture(params=["dot", "circo", "fdp", "neato"])
def layout_engine(request) -> str:
    """Parametrized fixture for different Graphviz layout engines."""
    return request.param


@pytest.fixture
def sample_lock_configurations() -> List[Dict[str, Any]]:
    """Provide sample lock configurations for testing."""
    return [
        {
            "type": "EXISTS",
            "property": "email",
            "expected_value": None
        },
        {
            "type": "REGEX",
            "property": "email",
            "expected_value": r"^[^@]+@[^@]+\.[^@]+$"
        },
        {
            "type": "EQUALS",
            "property": "status",
            "expected_value": "active"
        },
        {
            "type": "GREATER_THAN",
            "property": "age",
            "expected_value": 18
        },
        {
            "type": "IN_LIST",
            "property": "role",
            "expected_value": ["admin", "user", "moderator"]
        }
    ]


@pytest.fixture
def expected_mermaid_elements() -> Dict[str, List[str]]:
    """Provide expected elements for Mermaid diagram validation."""
    return {
        "overview": [
            "```mermaid",
            "flowchart TD",
            "S0[",
            "S1[",
            "S0 -->",
            "```"
        ],
        "detailed": [
            "```mermaid",
            "flowchart TD",
            "subgraph",
            "direction TB",
            "gate(s)",
            "```"
        ],
        "full": [
            "```mermaid",
            "flowchart TD",
            "%% Gate Details",
            "subgraph G",
            "validation gate",
            "```"
        ]
    }


@pytest.fixture
def expected_graphviz_elements() -> Dict[str, List[str]]:
    """Provide expected elements for Graphviz DOT validation."""
    return {
        "overview": [
            "digraph StageFlow {",
            "layout=dot;",
            "rankdir=TB;",
            "shape=house",
            "shape=box",
            "shape=invhouse",
            "}"
        ],
        "detailed": [
            "digraph StageFlow {",
            "layout=dot;",
            "(0 gates)",
            "\\n",
            "gates)",
            "}"
        ],
        "full": [
            "digraph StageFlow {",
            "// Gate details",
            "cluster_",
            "subgraph",
            "}"
        ]
    }


# Helper functions for test validation
def validate_mermaid_structure(diagram_content: str) -> bool:
    """Validate that Mermaid diagram has proper structure."""
    return (
        diagram_content.startswith("```mermaid") and
        diagram_content.endswith("```") and
        "flowchart TD" in diagram_content
    )


def validate_graphviz_structure(dot_content: str) -> bool:
    """Validate that Graphviz DOT has proper structure."""
    return (
        dot_content.startswith("digraph") and
        dot_content.endswith("}") and
        "layout=" in dot_content and
        "rankdir=" in dot_content
    )


def count_diagram_elements(content: str, element_type: str) -> int:
    """Count specific elements in diagram content."""
    if element_type == "mermaid_nodes":
        return content.count("[") - content.count("[[")  # Exclude subgraph brackets
    elif element_type == "mermaid_edges":
        return content.count("-->")
    elif element_type == "graphviz_nodes":
        return content.count(" [label=")
    elif element_type == "graphviz_edges":
        return content.count(" -> ") + content.count(" -- ")
    return 0