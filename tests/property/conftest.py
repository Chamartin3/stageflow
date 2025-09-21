"""Configuration for property-based tests.

This module configures Hypothesis settings for property-based testing,
ensuring appropriate test case generation and execution timeouts.
"""

import pytest
from hypothesis import HealthCheck, Verbosity, settings

# Default settings for property tests
settings.register_profile(
    "default",
    max_examples=100,
    deadline=5000,  # 5 seconds per test
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
)

# Fast settings for CI or quick testing
settings.register_profile(
    "fast",
    max_examples=50,
    deadline=2000,  # 2 seconds per test
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)

# Thorough settings for comprehensive testing
settings.register_profile(
    "thorough",
    max_examples=500,
    deadline=10000,  # 10 seconds per test
    suppress_health_check=[
        HealthCheck.too_slow,
    ],
)

# Development settings for debugging
settings.register_profile(
    "debug",
    max_examples=10,
    deadline=None,  # No timeout for debugging
    verbosity=Verbosity.verbose,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)

# Load the default profile
settings.load_profile("default")


@pytest.fixture(autouse=True)
def setup_hypothesis_for_property_tests():
    """Automatically set up Hypothesis for property tests."""
    # This fixture runs automatically for all tests in this module
    # and ensures consistent Hypothesis configuration
    pass
