"""Process schema fixtures for StageFlow testing.

This module provides process schema fixtures representing various workflow
patterns, from simple linear flows to complex branching and parallel processes.
"""

from typing import Any

import pytest


# Simple Workflow Schemas
@pytest.fixture
def simple_linear_schema() -> dict[str, Any]:
    """Simple linear process schema with two stages."""
    return {
        "process": {
            "name": "simple_onboarding",
            "description": "Basic user onboarding flow",
            "version": "1.0",
            "initial_stage": "registration",
            "final_stage": "active",
            "stages": [
                {
                    "name": "registration",
                    "description": "User registration and basic validation",
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
                             "name": "basic_validation",
                             "target_stage": "active",
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
                     ]
                },
                {
                    "name": "active",
                    "description": "Active user state",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


@pytest.fixture
def three_stage_linear_schema() -> dict[str, Any]:
    """Three-stage linear process for user onboarding."""
    return {
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
                        "field_types": {
                            "email": "string",
                            "password": "string"
                        }
                    },
                     "gates": [
                         {
                             "name": "registration_complete",
                             "target_stage": "profile_setup",
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
                     ]
                },
                {
                    "name": "profile_setup",
                    "description": "Profile completion",
                    "expected_schema": {
                        "required_fields": ["profile.first_name", "profile.last_name"],
                        "field_types": {
                            "profile.first_name": "string",
                            "profile.last_name": "string"
                        }
                    },
                     "gates": [
                         {
                             "name": "profile_complete",
                             "target_stage": "verified",
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
                     ]
                },
                {
                    "name": "verified",
                    "description": "Verified user state",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


# Complex Workflow Schemas
@pytest.fixture
def branching_workflow_schema() -> dict[str, Any]:
    """Complex workflow with conditional branching."""
    return {
        "process": {
            "name": "order_processing",
            "description": "E-commerce order processing with different payment flows",
            "version": "1.0",
            "initial_stage": "order_placed",
            "final_stage": "completed",
            "stages": [
                {
                    "name": "order_placed",
                    "description": "Initial order placement",
                    "expected_schema": {
                        "required_fields": ["order_id", "customer_id", "items", "payment.method"],
                        "field_types": {
                            "order_id": "string",
                            "customer_id": "string",
                            "payment.method": "string"
                        }
                    },
                    "gates": [
                        {
                            "name": "order_valid",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "order_id",
                                    "lock_type": "exists"
                                },
                                {
                                    "property_path": "items",
                                    "lock_type": "not_empty"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "payment_processing",
                            "condition": "order_valid"
                        }
                    ]
                },
                {
                    "name": "payment_processing",
                    "description": "Payment processing stage",
                    "gates": [
                        {
                            "name": "credit_card_payment",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "payment.method",
                                    "lock_type": "equals",
                                    "expected_value": "credit_card"
                                },
                                {
                                    "property_path": "payment.card_number",
                                    "lock_type": "exists"
                                }
                            ]
                        },
                        {
                            "name": "paypal_payment",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "payment.method",
                                    "lock_type": "equals",
                                    "expected_value": "paypal"
                                },
                                {
                                    "property_path": "payment.paypal_token",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "payment_approved",
                            "condition": "credit_card_payment OR paypal_payment"
                        },
                        {
                            "target_stage": "payment_failed",
                            "condition": "NOT (credit_card_payment OR paypal_payment)"
                        }
                    ]
                },
                {
                    "name": "payment_approved",
                    "description": "Payment successfully processed",
                    "gates": [],
                    "transitions": [
                        {
                            "target_stage": "fulfillment",
                            "condition": "auto"
                        }
                    ]
                },
                {
                    "name": "payment_failed",
                    "description": "Payment processing failed",
                    "gates": [
                        {
                            "name": "retry_available",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "payment.retry_count",
                                    "lock_type": "less_than",
                                    "expected_value": 3
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "payment_processing",
                            "condition": "retry_available"
                        },
                        {
                            "target_stage": "cancelled",
                            "condition": "NOT retry_available"
                        }
                    ]
                },
                {
                    "name": "fulfillment",
                    "description": "Order fulfillment",
                    "gates": [
                        {
                            "name": "ready_to_ship",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "shipping.address",
                                    "lock_type": "exists"
                                },
                                {
                                    "property_path": "inventory.available",
                                    "lock_type": "equals",
                                    "expected_value": True
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "shipped",
                            "condition": "ready_to_ship"
                        }
                    ]
                },
                {
                    "name": "shipped",
                    "description": "Order shipped",
                    "gates": [
                        {
                            "name": "delivered",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "shipping.delivered_at",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "completed",
                            "condition": "delivered"
                        }
                    ]
                },
                {
                    "name": "completed",
                    "description": "Order completed successfully",
                    "gates": [],
                    "transitions": []
                },
                {
                    "name": "cancelled",
                    "description": "Order cancelled",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


@pytest.fixture
def parallel_workflow_schema() -> dict[str, Any]:
    """Workflow with parallel processing stages."""
    return {
        "process": {
            "name": "content_review",
            "description": "Parallel content review process",
            "version": "1.0",
            "initial_stage": "submitted",
            "final_stage": "published",
            "stages": [
                {
                    "name": "submitted",
                    "description": "Content submitted for review",
                    "expected_schema": {
                        "required_fields": ["content", "author", "type"],
                        "field_types": {
                            "content": "string",
                            "author": "string",
                            "type": "string"
                        }
                    },
                    "gates": [
                        {
                            "name": "content_valid",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "content",
                                    "lock_type": "not_empty"
                                },
                                {
                                    "property_path": "author",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "technical_review",
                            "condition": "content_valid"
                        },
                        {
                            "target_stage": "editorial_review",
                            "condition": "content_valid"
                        },
                        {
                            "target_stage": "legal_review",
                            "condition": "content_valid"
                        }
                    ]
                },
                {
                    "name": "technical_review",
                    "description": "Technical accuracy review",
                    "gates": [
                        {
                            "name": "tech_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "reviews.technical.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "review_complete",
                            "condition": "tech_approved"
                        }
                    ]
                },
                {
                    "name": "editorial_review",
                    "description": "Editorial and style review",
                    "gates": [
                        {
                            "name": "editorial_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "reviews.editorial.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "review_complete",
                            "condition": "editorial_approved"
                        }
                    ]
                },
                {
                    "name": "legal_review",
                    "description": "Legal compliance review",
                    "gates": [
                        {
                            "name": "legal_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "reviews.legal.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "review_complete",
                            "condition": "legal_approved"
                        }
                    ]
                },
                {
                    "name": "review_complete",
                    "description": "All reviews completed",
                    "gates": [
                        {
                            "name": "all_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "reviews.technical.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                },
                                {
                                    "property_path": "reviews.editorial.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                },
                                {
                                    "property_path": "reviews.legal.status",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "published",
                            "condition": "all_approved"
                        }
                    ]
                },
                {
                    "name": "published",
                    "description": "Content published",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


# Error Scenario Schemas
@pytest.fixture
def invalid_process_schema() -> dict[str, Any]:
    """Process schema with intentional errors for testing validation."""
    return {
        "process": {
            "name": "",  # Invalid: empty name
            "description": "Process with validation errors",
            "version": "1.0",
            "initial_stage": "nonexistent_stage",  # Invalid: references non-existent stage
            "final_stage": "end",
            "stages": [
                {
                    "name": "start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "invalid_gate",
                            "logic": "INVALID_LOGIC",  # Invalid: unsupported logic type
                            "locks": [
                                {
                                    "property_path": "",  # Invalid: empty path
                                    "lock_type": "nonexistent_type",  # Invalid: unsupported lock type
                                    "expected_value": None
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "nonexistent_target",  # Invalid: references non-existent stage
                            "condition": "invalid_gate"
                        }
                    ]
                },
                {
                    "name": "start",  # Invalid: duplicate stage name
                    "description": "Duplicate stage",
                    "gates": [],
                    "transitions": []
                }
                # Missing final stage "end"
            ]
        }
    }


@pytest.fixture
def circular_dependency_schema() -> dict[str, Any]:
    """Process schema with circular dependencies."""
    return {
        "process": {
            "name": "circular_process",
            "description": "Process with circular stage dependencies",
            "version": "1.0",
            "initial_stage": "stage_a",
            "final_stage": "stage_c",
            "stages": [
                {
                    "name": "stage_a",
                    "description": "Stage A",
                    "gates": [
                        {
                            "name": "gate_a",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "field_a",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "stage_b",
                            "condition": "gate_a"
                        }
                    ]
                },
                {
                    "name": "stage_b",
                    "description": "Stage B",
                    "gates": [
                        {
                            "name": "gate_b",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "field_b",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "stage_a",  # Creates circular dependency
                            "condition": "gate_b"
                        },
                        {
                            "target_stage": "stage_c",
                            "condition": "gate_b"
                        }
                    ]
                },
                {
                    "name": "stage_c",
                    "description": "Stage C (Final)",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


# Performance Test Schemas
@pytest.fixture
def large_process_schema() -> dict[str, Any]:
    """Large process schema for performance testing."""
    stages = []

    # Create 50 stages with multiple gates and locks each
    for i in range(50):
        stage_name = f"stage_{i:02d}"
        next_stage = f"stage_{i+1:02d}" if i < 49 else "final_stage"

        # Create multiple gates per stage
        gates = []
        for j in range(5):  # 5 gates per stage
            gate_name = f"gate_{i:02d}_{j}"
            locks = []

            # Create multiple locks per gate
            for k in range(3):  # 3 locks per gate
                locks.append({
                    "property_path": f"data.section_{i}.field_{j}_{k}",
                    "lock_type": "exists"
                })

            gates.append({
                "name": gate_name,
                "logic": "AND",
                "locks": locks
            })

        stages.append({
            "name": stage_name,
            "description": f"Automated stage {i}",
            "gates": gates,
            "transitions": [
                {
                    "target_stage": next_stage,
                    "condition": f"gate_{i:02d}_0"
                }
            ]
        })

    # Add final stage
    stages.append({
        "name": "final_stage",
        "description": "Final stage",
        "gates": [],
        "transitions": []
    })

    return {
        "process": {
            "name": "large_performance_test",
            "description": "Large process for performance testing",
            "version": "1.0",
            "initial_stage": "stage_00",
            "final_stage": "final_stage",
            "stages": stages
        }
    }


# Domain-Specific Schemas
@pytest.fixture
def hr_onboarding_schema() -> dict[str, Any]:
    """HR employee onboarding process schema."""
    return {
        "process": {
            "name": "employee_onboarding",
            "description": "HR employee onboarding process",
            "version": "1.0",
            "initial_stage": "application_received",
            "final_stage": "onboarded",
            "stages": [
                {
                    "name": "application_received",
                    "description": "Job application received",
                    "expected_schema": {
                        "required_fields": ["applicant.name", "applicant.email", "position"],
                        "field_types": {
                            "applicant.name": "string",
                            "applicant.email": "string",
                            "position": "string"
                        }
                    },
                    "gates": [
                        {
                            "name": "application_complete",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "applicant.resume",
                                    "lock_type": "exists"
                                },
                                {
                                    "property_path": "applicant.cover_letter",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "screening",
                            "condition": "application_complete"
                        }
                    ]
                },
                {
                    "name": "screening",
                    "description": "Initial screening",
                    "gates": [
                        {
                            "name": "screening_passed",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "screening.status",
                                    "lock_type": "equals",
                                    "expected_value": "passed"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "interview",
                            "condition": "screening_passed"
                        }
                    ]
                },
                {
                    "name": "interview",
                    "description": "Interview process",
                    "gates": [
                        {
                            "name": "interview_successful",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "interview.score",
                                    "lock_type": "greater_than",
                                    "expected_value": 7
                                },
                                {
                                    "property_path": "interview.recommendation",
                                    "lock_type": "equals",
                                    "expected_value": "hire"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "offer_extended",
                            "condition": "interview_successful"
                        }
                    ]
                },
                {
                    "name": "offer_extended",
                    "description": "Job offer extended",
                    "gates": [
                        {
                            "name": "offer_accepted",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "offer.status",
                                    "lock_type": "equals",
                                    "expected_value": "accepted"
                                },
                                {
                                    "property_path": "background_check.status",
                                    "lock_type": "equals",
                                    "expected_value": "cleared"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "onboarded",
                            "condition": "offer_accepted"
                        }
                    ]
                },
                {
                    "name": "onboarded",
                    "description": "Employee successfully onboarded",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }


@pytest.fixture
def financial_loan_schema() -> dict[str, Any]:
    """Financial loan approval process schema."""
    return {
        "process": {
            "name": "loan_approval",
            "description": "Financial institution loan approval process",
            "version": "1.0",
            "initial_stage": "application_submitted",
            "final_stage": "loan_approved",
            "stages": [
                {
                    "name": "application_submitted",
                    "description": "Loan application submitted",
                    "expected_schema": {
                        "required_fields": [
                            "applicant.ssn", "applicant.income", "loan.amount", "loan.purpose"
                        ],
                        "field_types": {
                            "applicant.income": "number",
                            "loan.amount": "number"
                        }
                    },
                    "gates": [
                        {
                            "name": "basic_eligibility",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "applicant.age",
                                    "lock_type": "greater_than",
                                    "expected_value": 18
                                },
                                {
                                    "property_path": "applicant.income",
                                    "lock_type": "greater_than",
                                    "expected_value": 25000
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "credit_check",
                            "condition": "basic_eligibility"
                        }
                    ]
                },
                {
                    "name": "credit_check",
                    "description": "Credit history verification",
                    "gates": [
                        {
                            "name": "credit_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "credit.score",
                                    "lock_type": "greater_than",
                                    "expected_value": 650
                                },
                                {
                                    "property_path": "credit.bankruptcies",
                                    "lock_type": "equals",
                                    "expected_value": 0
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "income_verification",
                            "condition": "credit_approved"
                        }
                    ]
                },
                {
                    "name": "income_verification",
                    "description": "Income and employment verification",
                    "gates": [
                        {
                            "name": "income_verified",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "employment.verified",
                                    "lock_type": "equals",
                                    "expected_value": True
                                },
                                {
                                    "property_path": "debt_to_income_ratio",
                                    "lock_type": "less_than",
                                    "expected_value": 0.43
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "underwriting",
                            "condition": "income_verified"
                        }
                    ]
                },
                {
                    "name": "underwriting",
                    "description": "Loan underwriting review",
                    "gates": [
                        {
                            "name": "underwriting_approved",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "underwriting.decision",
                                    "lock_type": "equals",
                                    "expected_value": "approved"
                                },
                                {
                                    "property_path": "underwriting.risk_level",
                                    "lock_type": "in_list",
                                    "expected_value": ["low", "medium"]
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "loan_approved",
                            "condition": "underwriting_approved"
                        }
                    ]
                },
                {
                    "name": "loan_approved",
                    "description": "Loan approved and ready for funding",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }
