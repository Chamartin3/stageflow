"""Parameterized fixture definitions for StageFlow testing.

This module provides parameterized fixtures that enable comprehensive testing
across different configurations, input variations, and edge cases.
"""

from typing import Any

import pytest

from stageflow.gates import LockType


# Configuration Variants
@pytest.fixture(params=[
    {"theme": "light", "language": "en", "notifications": True},
    {"theme": "dark", "language": "en", "notifications": False},
    {"theme": "auto", "language": "es", "notifications": True},
    {"theme": "light", "language": "fr", "notifications": False},
])
def user_preference_variants(request) -> dict[str, Any]:
    """Various user preference configurations for testing."""
    return request.param


@pytest.fixture(params=[
    {"verification": {"email": True, "phone": True, "identity": True}},
    {"verification": {"email": True, "phone": False, "identity": False}},
    {"verification": {"email": False, "phone": True, "identity": False}},
    {"verification": {"email": False, "phone": False, "identity": False}},
])
def verification_state_variants(request) -> dict[str, Any]:
    """Different verification state combinations."""
    return request.param


@pytest.fixture(params=[
    "pending", "processing", "approved", "rejected", "completed", "cancelled", "failed"
])
def status_variants(request) -> str:
    """Various status values for testing state transitions."""
    return request.param


# Input Validation Sets
@pytest.fixture(params=[
    # Valid emails
    ("user@example.com", True),
    ("test.email+tag@domain.co.uk", True),
    ("user123@test-domain.org", True),
    # Invalid emails
    ("", False),
    ("notanemail", False),
    ("@example.com", False),
    ("user@", False),
    ("user@@example.com", False),
    ("user name@example.com", False),
])
def email_validation_cases(request) -> tuple[str, bool]:
    """Email validation test cases with expected results."""
    return request.param


@pytest.fixture(params=[
    # Valid passwords
    ("Password123!", True),
    ("MySecure@Pass1", True),
    ("Complex#Password2024", True),
    # Invalid passwords
    ("", False),
    ("short", False),
    ("nouppercaseorspecial123", False),
    ("NOLOWERCASEORSPECIAL123", False),
    ("NoSpecialChars123", False),
    ("NoNumbers@SpecialChars", False),
])
def password_validation_cases(request) -> tuple[str, bool]:
    """Password validation test cases with strength requirements."""
    return request.param


@pytest.fixture(params=[
    # Valid ages
    (18, True),
    (25, True),
    (65, True),
    (100, True),
    # Invalid ages
    (17, False),
    (-5, False),
    (150, False),
    (0, False),
])
def age_validation_cases(request) -> tuple[int, bool]:
    """Age validation test cases for adult verification."""
    return request.param


@pytest.fixture(params=[
    # Valid phone numbers
    ("+1-555-0123", True),
    ("+44-20-7946-0958", True),
    ("+33-1-23-45-67-89", True),
    ("555-0123", True),
    # Invalid phone numbers
    ("", False),
    ("abc-def-ghij", False),
    ("123", False),
    ("+", False),
])
def phone_validation_cases(request) -> tuple[str, bool]:
    """Phone number validation test cases."""
    return request.param


# Error Condition Parameters
@pytest.fixture(params=[
    {"property_path": "", "error_type": "InvalidPathError"},
    {"property_path": "nonexistent.field", "error_type": "PropertyNotFoundError"},
    {"property_path": "invalid..path", "error_type": "InvalidPathError"},
    {"property_path": "array[-1]", "error_type": "IndexError"},
    {"property_path": "array[999]", "error_type": "IndexError"},
])
def property_path_error_cases(request) -> dict[str, str]:
    """Property path error scenarios for testing error handling."""
    return request.param


@pytest.fixture(params=[
    {"lock_type": "nonexistent_type", "error_type": "ValueError"},
    {"lock_type": LockType.EQUALS, "expected_value": None, "error_type": "ValueError"},
    {"lock_type": LockType.CUSTOM, "validator_name": None, "error_type": "ValueError"},
    {"lock_type": LockType.REGEX, "expected_value": "[invalid regex", "error_type": "ValueError"},
])
def lock_configuration_error_cases(request) -> dict[str, Any]:
    """Lock configuration error scenarios."""
    return request.param


# Performance Test Parameters
@pytest.fixture(params=[
    {"element_count": 10, "property_depth": 3},
    {"element_count": 100, "property_depth": 5},
    {"element_count": 1000, "property_depth": 7},
    {"element_count": 5000, "property_depth": 10},
])
def performance_test_parameters(request) -> dict[str, int]:
    """Performance test parameters for different scales."""
    return request.param


@pytest.fixture(params=[
    {"locks_per_gate": 1, "gates_per_stage": 1, "stages_per_process": 2},
    {"locks_per_gate": 3, "gates_per_stage": 2, "stages_per_process": 5},
    {"locks_per_gate": 5, "gates_per_stage": 3, "stages_per_process": 10},
    {"locks_per_gate": 10, "gates_per_stage": 5, "stages_per_process": 20},
])
def process_complexity_parameters(request) -> dict[str, int]:
    """Process complexity parameters for scalability testing."""
    return request.param


# Data Type Variations
@pytest.fixture(params=[
    # String variations
    ("", "empty_string"),
    ("normal_string", "normal_string"),
    ("   whitespace   ", "whitespace_string"),
    ("unicode_string_🚀", "unicode_string"),
    ("very_long_string_" + "x" * 1000, "long_string"),
    # Numeric variations
    (0, "zero"),
    (42, "positive_int"),
    (-42, "negative_int"),
    (3.14159, "float"),
    (float('inf'), "infinity"),
    (float('-inf'), "negative_infinity"),
    # Boolean variations
    (True, "true"),
    (False, "false"),
    # None and null
    (None, "none"),
    # Collection variations
    ([], "empty_list"),
    ([1, 2, 3], "simple_list"),
    ([1, "mixed", {"nested": True}], "mixed_list"),
    ({}, "empty_dict"),
    ({"key": "value"}, "simple_dict"),
    ({"nested": {"deeply": {"value": "found"}}}, "nested_dict"),
])
def data_type_variations(request) -> tuple[Any, str]:
    """Various data types and values for comprehensive testing."""
    return request.param


@pytest.fixture(params=[
    # Valid JSON-like structures
    ({"valid": "json"}, True),
    ({"nested": {"structure": True}}, True),
    ({"array": [1, 2, 3]}, True),
    # Invalid structures (from Element perspective)
    (None, False),
    ("not_a_dict", False),
    ([], False),
    (42, False),
])
def element_data_variations(request) -> tuple[Any, bool]:
    """Element data variations for testing data type handling."""
    return request.param


# Lock Type Test Parameters
@pytest.fixture(params=[
    (LockType.EXISTS, "field", None, True),
    (LockType.EXISTS, "nonexistent", None, False),
    (LockType.EQUALS, "field", "value", True),
    (LockType.EQUALS, "field", "wrong_value", False),
    (LockType.GREATER_THAN, "number_field", 5, True),
    (LockType.GREATER_THAN, "number_field", 15, False),
    (LockType.LESS_THAN, "number_field", 15, True),
    (LockType.LESS_THAN, "number_field", 5, False),
    (LockType.CONTAINS, "text_field", "substring", True),
    (LockType.CONTAINS, "text_field", "missing", False),
    (LockType.REGEX, "email", r"^[^@]+@[^@]+\.[^@]+$", True),
    (LockType.REGEX, "invalid_email", r"^[^@]+@[^@]+\.[^@]+$", False),
    (LockType.TYPE_CHECK, "string_field", str, True),
    (LockType.TYPE_CHECK, "string_field", int, False),
    (LockType.RANGE, "score", [0, 100], True),
    (LockType.RANGE, "score", [50, 60], False),
    (LockType.LENGTH, "items", 3, True),
    (LockType.LENGTH, "items", 5, False),
    (LockType.NOT_EMPTY, "text_field", None, True),
    (LockType.NOT_EMPTY, "empty_field", None, False),
    (LockType.IN_LIST, "status", ["active", "pending"], True),
    (LockType.IN_LIST, "status", ["archived", "deleted"], False),
    (LockType.NOT_IN_LIST, "status", ["archived", "deleted"], True),
    (LockType.NOT_IN_LIST, "status", ["active", "pending"], False),
])
def lock_type_test_cases(request) -> tuple[LockType, str, Any, bool]:
    """Comprehensive lock type test cases with expected results."""
    return request.param


# Edge Case Collections
@pytest.fixture(params=[
    # Boundary values
    {"int_max": 2**63 - 1, "int_min": -(2**63), "zero": 0},
    {"float_max": 1.7976931348623157e+308, "float_min": -1.7976931348623157e+308},
    {"tiny_positive": 1e-10, "tiny_negative": -1e-10},
    # Empty collections
    {"empty_list": [], "empty_dict": {}, "empty_string": ""},
    # Large collections
    {"large_list": list(range(10000)), "large_string": "x" * 100000},
    # Special characters
    {"special_chars": "!@#$%^&*()[]{}|\\:;\"'<>?/~`"},
    {"unicode_mix": "Hello 世界 🌍 émojis ñoño"},
    {"control_chars": "\t\n\r\x00\x1f"},
])
def edge_case_collections(request) -> dict[str, Any]:
    """Collections of edge case values for boundary testing."""
    return request.param


# Workflow Pattern Parameters
@pytest.fixture(params=[
    {"pattern": "linear", "stages": 3, "complexity": "simple"},
    {"pattern": "branching", "stages": 5, "complexity": "medium"},
    {"pattern": "parallel", "stages": 4, "complexity": "medium"},
    {"pattern": "circular", "stages": 6, "complexity": "complex"},
    {"pattern": "hierarchical", "stages": 8, "complexity": "complex"},
])
def workflow_pattern_parameters(request) -> dict[str, Any]:
    """Workflow pattern parameters for testing different process types."""
    return request.param


# Concurrency Test Parameters
@pytest.fixture(params=[
    {"thread_count": 1, "operations_per_thread": 100},
    {"thread_count": 5, "operations_per_thread": 50},
    {"thread_count": 10, "operations_per_thread": 20},
    {"thread_count": 20, "operations_per_thread": 10},
])
def concurrency_test_parameters(request) -> dict[str, int]:
    """Concurrency test parameters for thread safety testing."""
    return request.param


# Memory Test Parameters
@pytest.fixture(params=[
    {"object_count": 1000, "object_size": "small"},
    {"object_count": 5000, "object_size": "medium"},
    {"object_count": 10000, "object_size": "large"},
    {"object_count": 50000, "object_size": "xlarge"},
])
def memory_test_parameters(request) -> dict[str, Any]:
    """Memory usage test parameters for stress testing."""
    return request.param


# Locale and Internationalization Parameters
@pytest.fixture(params=[
    {"locale": "en_US", "encoding": "utf-8", "timezone": "UTC"},
    {"locale": "es_ES", "encoding": "utf-8", "timezone": "Europe/Madrid"},
    {"locale": "zh_CN", "encoding": "utf-8", "timezone": "Asia/Shanghai"},
    {"locale": "ar_SA", "encoding": "utf-8", "timezone": "Asia/Riyadh"},
    {"locale": "de_DE", "encoding": "utf-8", "timezone": "Europe/Berlin"},
])
def internationalization_parameters(request) -> dict[str, str]:
    """Internationalization parameters for testing locale support."""
    return request.param


# Database Operation Parameters
@pytest.fixture(params=[
    {"operation": "create", "batch_size": 1, "timeout": 1.0},
    {"operation": "read", "batch_size": 10, "timeout": 0.5},
    {"operation": "update", "batch_size": 5, "timeout": 2.0},
    {"operation": "delete", "batch_size": 3, "timeout": 1.5},
])
def database_operation_parameters(request) -> dict[str, Any]:
    """Database operation parameters for testing persistence layers."""
    return request.param


# API Response Parameters
@pytest.fixture(params=[
    {"status_code": 200, "response_time": 0.1, "payload_size": "small"},
    {"status_code": 201, "response_time": 0.2, "payload_size": "medium"},
    {"status_code": 400, "response_time": 0.05, "payload_size": "error"},
    {"status_code": 404, "response_time": 0.03, "payload_size": "error"},
    {"status_code": 500, "response_time": 1.0, "payload_size": "error"},
    {"status_code": 503, "response_time": 5.0, "payload_size": "error"},
])
def api_response_parameters(request) -> dict[str, Any]:
    """API response parameters for testing external service interactions."""
    return request.param


# Security Test Parameters
@pytest.fixture(params=[
    {"attack_type": "sql_injection", "payload": "'; DROP TABLE users; --"},
    {"attack_type": "xss", "payload": "<script>alert('xss')</script>"},
    {"attack_type": "path_traversal", "payload": "../../etc/passwd"},
    {"attack_type": "command_injection", "payload": "; rm -rf /"},
    {"attack_type": "ldap_injection", "payload": "*()|&'"},
])
def security_test_parameters(request) -> dict[str, str]:
    """Security test parameters for testing input validation."""
    return request.param


# Error Recovery Parameters
@pytest.fixture(params=[
    {"error_type": "network_timeout", "retry_count": 3, "backoff": "exponential"},
    {"error_type": "database_connection", "retry_count": 5, "backoff": "linear"},
    {"error_type": "rate_limit", "retry_count": 10, "backoff": "fixed"},
    {"error_type": "service_unavailable", "retry_count": 2, "backoff": "none"},
])
def error_recovery_parameters(request) -> dict[str, Any]:
    """Error recovery parameters for testing resilience."""
    return request.param


# File Format Parameters
@pytest.fixture(params=[
    {"format": "yaml", "extension": ".yaml", "mime_type": "application/x-yaml"},
    {"format": "json", "extension": ".json", "mime_type": "application/json"},
    {"format": "xml", "extension": ".xml", "mime_type": "application/xml"},
    {"format": "csv", "extension": ".csv", "mime_type": "text/csv"},
])
def file_format_parameters(request) -> dict[str, str]:
    """File format parameters for testing different serialization formats."""
    return request.param
