"""Sample data fixtures for StageFlow testing.

This module provides realistic sample datasets, edge case data, and large
datasets for comprehensive testing scenarios across different domains.
"""

import random
from datetime import datetime, timedelta
from typing import Any

import pytest


# Basic Sample Data Sets
@pytest.fixture
def sample_users() -> list[dict[str, Any]]:
    """Collection of sample user data for batch testing."""
    return [
        {
            "id": "usr_001",
            "email": "alice@example.com",
            "username": "alice_smith",
            "profile": {
                "first_name": "Alice",
                "last_name": "Smith",
                "display_name": "Alice S.",
                "bio": "Software engineer passionate about clean code",
                "phone": "+1-555-0101",
                "birthdate": "1985-03-15",
                "timezone": "America/New_York"
            },
            "preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "theme": "dark",
                "language": "en"
            },
            "verification": {
                "email_verified": True,
                "phone_verified": True,
                "identity_verified": False
            },
            "metadata": {
                "created_at": "2024-01-01T08:00:00Z",
                "updated_at": "2024-01-15T14:30:00Z",
                "last_login": "2024-01-20T09:15:00Z",
                "login_count": 156,
                "source": "web"
            }
        },
        {
            "id": "usr_002",
            "email": "bob@company.org",
            "username": "bob_jones",
            "profile": {
                "first_name": "Bob",
                "last_name": "Jones",
                "display_name": "Bobby",
                "bio": "Product manager building amazing experiences",
                "phone": "+1-555-0102",
                "birthdate": "1992-07-22",
                "timezone": "America/Los_Angeles"
            },
            "preferences": {
                "email_notifications": False,
                "push_notifications": True,
                "theme": "light",
                "language": "en"
            },
            "verification": {
                "email_verified": True,
                "phone_verified": False,
                "identity_verified": True
            },
            "metadata": {
                "created_at": "2024-01-05T12:00:00Z",
                "updated_at": "2024-01-18T16:45:00Z",
                "last_login": "2024-01-19T20:30:00Z",
                "login_count": 89,
                "source": "mobile"
            }
        },
        {
            "id": "usr_003",
            "email": "charlie@startup.io",
            "username": "charlie_dev",
            "profile": {
                "first_name": "Charlie",
                "last_name": "Wilson",
                "display_name": "Charlie W.",
                "bio": "Full-stack developer and coffee enthusiast",
                "phone": "+1-555-0103",
                "birthdate": "1988-11-08",
                "timezone": "Europe/London"
            },
            "preferences": {
                "email_notifications": True,
                "push_notifications": False,
                "theme": "auto",
                "language": "en"
            },
            "verification": {
                "email_verified": False,
                "phone_verified": False,
                "identity_verified": False
            },
            "metadata": {
                "created_at": "2024-01-10T15:30:00Z",
                "updated_at": "2024-01-10T15:30:00Z",
                "last_login": None,
                "login_count": 0,
                "source": "api"
            }
        }
    ]


@pytest.fixture
def sample_orders() -> list[dict[str, Any]]:
    """Collection of sample order data for e-commerce testing."""
    return [
        {
            "order_id": "ORD-2024-001",
            "customer_id": "usr_001",
            "status": "completed",
            "items": [
                {
                    "id": "item_001",
                    "name": "Premium Coffee Beans",
                    "sku": "COFFEE-PREM-001",
                    "quantity": 2,
                    "unit_price": 24.99,
                    "total_price": 49.98,
                    "category": "food_beverage"
                }
            ],
            "shipping": {
                "method": "express",
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "state": "NY",
                    "zip": "10001",
                    "country": "US"
                },
                "estimated_delivery": "2024-01-22",
                "actual_delivery": "2024-01-21",
                "tracking_number": "TRK-ABC123"
            },
            "payment": {
                "method": "credit_card",
                "status": "completed",
                "amount": 55.97,
                "currency": "USD",
                "transaction_id": "TXN-DEF456",
                "payment_date": "2024-01-20T10:00:00Z"
            },
            "totals": {
                "subtotal": 49.98,
                "tax": 4.00,
                "shipping": 1.99,
                "discount": 0.00,
                "total": 55.97
            },
            "timestamps": {
                "created": "2024-01-20T10:00:00Z",
                "updated": "2024-01-21T16:30:00Z"
            }
        },
        {
            "order_id": "ORD-2024-002",
            "customer_id": "usr_002",
            "status": "pending",
            "items": [
                {
                    "id": "item_002",
                    "name": "Wireless Headphones",
                    "sku": "AUDIO-WL-001",
                    "quantity": 1,
                    "unit_price": 129.99,
                    "total_price": 129.99,
                    "category": "electronics"
                },
                {
                    "id": "item_003",
                    "name": "Phone Case",
                    "sku": "CASE-PH-001",
                    "quantity": 2,
                    "unit_price": 19.99,
                    "total_price": 39.98,
                    "category": "accessories"
                }
            ],
            "shipping": {
                "method": "standard",
                "address": {
                    "street": "456 Oak Ave",
                    "city": "Los Angeles",
                    "state": "CA",
                    "zip": "90210",
                    "country": "US"
                },
                "estimated_delivery": "2024-01-28",
                "actual_delivery": None,
                "tracking_number": None
            },
            "payment": {
                "method": "paypal",
                "status": "pending",
                "amount": 184.36,
                "currency": "USD",
                "transaction_id": None,
                "payment_date": None
            },
            "totals": {
                "subtotal": 169.97,
                "tax": 13.60,
                "shipping": 0.79,
                "discount": 0.00,
                "total": 184.36
            },
            "timestamps": {
                "created": "2024-01-21T14:30:00Z",
                "updated": "2024-01-21T14:30:00Z"
            }
        }
    ]


@pytest.fixture
def sample_products() -> list[dict[str, Any]]:
    """Collection of sample product data for catalog testing."""
    return [
        {
            "id": "prod_001",
            "name": "Premium Coffee Beans",
            "sku": "COFFEE-PREM-001",
            "description": "High-quality arabica coffee beans from sustainable farms",
            "category": "food_beverage",
            "subcategory": "coffee",
            "price": 24.99,
            "currency": "USD",
            "inventory": {
                "stock_quantity": 150,
                "reserved_quantity": 5,
                "available_quantity": 145,
                "reorder_level": 20,
                "warehouse_location": "A-12-3"
            },
            "attributes": {
                "weight": "1 lb",
                "origin": "Colombia",
                "roast_level": "medium",
                "organic": True,
                "fair_trade": True
            },
            "images": [
                "https://example.com/images/coffee_001_main.jpg",
                "https://example.com/images/coffee_001_detail.jpg"
            ],
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z"
        },
        {
            "id": "prod_002",
            "name": "Wireless Headphones",
            "sku": "AUDIO-WL-001",
            "description": "Premium wireless headphones with noise cancellation",
            "category": "electronics",
            "subcategory": "audio",
            "price": 129.99,
            "currency": "USD",
            "inventory": {
                "stock_quantity": 75,
                "reserved_quantity": 2,
                "available_quantity": 73,
                "reorder_level": 10,
                "warehouse_location": "B-05-1"
            },
            "attributes": {
                "color": "black",
                "battery_life": "30 hours",
                "wireless": True,
                "noise_cancellation": True,
                "warranty": "2 years"
            },
            "images": [
                "https://example.com/images/headphones_001_main.jpg",
                "https://example.com/images/headphones_001_side.jpg"
            ],
            "status": "active",
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-18T09:30:00Z"
        }
    ]


# Edge Case Data
@pytest.fixture
def edge_case_data() -> dict[str, dict[str, Any]]:
    """Collection of edge case data for boundary testing."""
    return {
        "empty_values": {
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
            "null_value": None,
            "zero_int": 0,
            "zero_float": 0.0,
            "false_bool": False
        },
        "boundary_values": {
            "max_int": 9223372036854775807,  # Max 64-bit signed int
            "min_int": -9223372036854775808,
            "max_float": 1.7976931348623157e+308,
            "min_float": -1.7976931348623157e+308,
            "tiny_positive": 1e-10,
            "tiny_negative": -1e-10
        },
        "string_edge_cases": {
            "single_char": "a",
            "very_long": "x" * 10000,
            "unicode_mix": "Hello 世界 🌍 émojis ñoño",
            "special_chars": "!@#$%^&*()[]{}|\\:;\"'<>?/~`",
            "whitespace_only": "   \t\n\r   ",
            "leading_trailing": "  value  ",
            "newlines": "line1\nline2\rline3\r\nline4",
            "escaped": "quote: \"hello\", backslash: \\, tab: \t"
        },
        "malformed_structures": {
            "mixed_types_list": [1, "two", {"three": 3}, None, True],
            "inconsistent_nested": {
                "users": [
                    {"name": "Alice", "age": 30},
                    {"name": "Bob"},  # Missing age
                    {"age": 25},      # Missing name
                    None              # Null entry
                ]
            },
            "circular_reference": None  # Cannot create in JSON, represents self-reference
        }
    }


@pytest.fixture
def invalid_email_samples() -> list[str]:
    """Collection of invalid email formats for validation testing."""
    return [
        "",                          # Empty string
        "notanemail",               # No @ symbol
        "@example.com",             # Missing local part
        "user@",                    # Missing domain
        "user@@example.com",        # Double @
        "user@.com",                # Missing domain name
        "user@com",                 # Missing TLD separator
        "user name@example.com",    # Space in local part
        "user@exam ple.com",        # Space in domain
        "user@",                    # Incomplete
        ".user@example.com",        # Leading dot
        "user.@example.com",        # Trailing dot
        "user..name@example.com",   # Double dots
        "user@example..com",        # Double dots in domain
        "user@-example.com",        # Hyphen at start of domain
        "user@example-.com",        # Hyphen at end of domain part
        "verylongusernamethatexceedsthenormallengthforvalidemail@example.com",  # Too long
        "user@" + "x" * 253 + ".com"  # Domain too long
    ]


@pytest.fixture
def valid_email_samples() -> list[str]:
    """Collection of valid email formats for validation testing."""
    return [
        "user@example.com",
        "test.email@example.org",
        "user+tag@example.net",
        "user123@test123.co.uk",
        "a@b.co",
        "very.long.email.address@very.long.domain.name.example.com",
        "user_name@example-domain.com",
        "123@example.com",
        "email@subdomain.example.com",
        "firstname-lastname@example.com"
    ]


# Large Dataset Fixtures
@pytest.fixture
def large_user_dataset() -> list[dict[str, Any]]:
    """Large dataset of users for performance testing."""
    users = []
    base_date = datetime(2024, 1, 1)

    for i in range(1000):
        user_id = f"usr_{i:04d}"
        created_date = base_date + timedelta(days=random.randint(0, 365))
        updated_date = created_date + timedelta(days=random.randint(0, 30))

        users.append({
            "id": user_id,
            "email": f"user{i}@example{i % 10}.com",
            "username": f"user_{i}",
            "profile": {
                "first_name": f"FirstName{i}",
                "last_name": f"LastName{i}",
                "display_name": f"User {i}",
                "bio": f"Bio for user {i}" if i % 3 == 0 else None,
                "phone": f"+1-555-{i:04d}" if i % 2 == 0 else None,
                "birthdate": f"{1980 + (i % 40)}-{1 + (i % 12):02d}-{1 + (i % 28):02d}",
                "timezone": ["UTC", "America/New_York", "America/Los_Angeles", "Europe/London"][i % 4]
            },
            "preferences": {
                "email_notifications": i % 2 == 0,
                "push_notifications": i % 3 == 0,
                "theme": ["light", "dark", "auto"][i % 3],
                "language": "en"
            },
            "verification": {
                "email_verified": i % 4 != 0,
                "phone_verified": i % 6 == 0,
                "identity_verified": i % 10 == 0
            },
            "metadata": {
                "created_at": created_date.isoformat() + "Z",
                "updated_at": updated_date.isoformat() + "Z",
                "last_login": (updated_date + timedelta(days=random.randint(0, 7))).isoformat() + "Z" if i % 5 != 0 else None,
                "login_count": random.randint(0, 500),
                "source": ["web", "mobile", "api"][i % 3],
                "tags": [f"tag_{j}" for j in range(i % 4)]
            }
        })

    return users


@pytest.fixture
def performance_test_data() -> dict[str, Any]:
    """Performance test data with various sizes."""
    return {
        "small_dataset": {
            "users": 10,
            "orders": 20,
            "products": 15
        },
        "medium_dataset": {
            "users": 100,
            "orders": 500,
            "products": 200
        },
        "large_dataset": {
            "users": 1000,
            "orders": 5000,
            "products": 2000
        },
        "xl_dataset": {
            "users": 10000,
            "orders": 50000,
            "products": 20000
        }
    }


# Nested Structure Fixtures
@pytest.fixture
def deeply_nested_element() -> dict[str, Any]:
    """Deeply nested structure for testing complex path resolution."""
    return {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "level5": {
                            "level6": {
                                "level7": {
                                    "level8": {
                                        "level9": {
                                            "level10": {
                                                "deep_value": "found_it",
                                                "deep_list": [
                                                    {"item": 0},
                                                    {"item": 1, "nested": {"value": "nested_in_list"}},
                                                    {"item": 2}
                                                ],
                                                "deep_dict": {
                                                    "key1": "value1",
                                                    "key2": {
                                                        "subkey": "subvalue"
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "arrays": {
            "mixed_array": [
                {"type": "object", "value": 1},
                "string_value",
                42,
                [1, 2, 3],
                {
                    "nested_in_array": {
                        "deeply": {
                            "nested": "array_nested_value"
                        }
                    }
                }
            ],
            "array_of_arrays": [
                [1, 2, 3],
                [{"nested": "value"}, {"another": "item"}],
                [[["deeply", "nested"], "array"]]
            ]
        }
    }


@pytest.fixture
def complex_json_like_structure() -> dict[str, Any]:
    """Complex JSON-like structure simulating real-world API responses."""
    return {
        "meta": {
            "api_version": "2.1",
            "request_id": "req_abc123",
            "timestamp": "2024-01-20T15:30:00Z",
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total_pages": 10,
                "total_items": 487
            }
        },
        "data": {
            "organization": {
                "id": "org_001",
                "name": "Test Organization",
                "settings": {
                    "features": {
                        "advanced_analytics": True,
                        "custom_branding": False,
                        "api_access": True
                    },
                    "integrations": {
                        "slack": {
                            "enabled": True,
                            "webhook_url": "https://hooks.slack.com/services/...",
                            "channels": ["#general", "#alerts"]
                        },
                        "email": {
                            "enabled": True,
                            "provider": "sendgrid",
                            "templates": {
                                "welcome": "tmpl_001",
                                "notification": "tmpl_002"
                            }
                        }
                    }
                }
            },
            "users": [
                {
                    "id": "usr_001",
                    "profile": {
                        "personal": {
                            "name": {
                                "first": "John",
                                "middle": "Q",
                                "last": "Public"
                            },
                            "contact": {
                                "emails": [
                                    {"type": "primary", "address": "john@example.com", "verified": True},
                                    {"type": "work", "address": "john.public@company.com", "verified": False}
                                ],
                                "phones": [
                                    {"type": "mobile", "number": "+1-555-0101", "verified": True},
                                    {"type": "work", "number": "+1-555-0102", "verified": False}
                                ]
                            }
                        },
                        "professional": {
                            "title": "Senior Software Engineer",
                            "department": "Engineering",
                            "manager": {
                                "id": "usr_002",
                                "name": "Jane Smith"
                            },
                            "skills": ["Python", "JavaScript", "AWS", "Docker"],
                            "certifications": [
                                {
                                    "name": "AWS Certified Solutions Architect",
                                    "issued_date": "2023-06-15",
                                    "expiry_date": "2026-06-15",
                                    "authority": "Amazon Web Services"
                                }
                            ]
                        }
                    },
                    "permissions": {
                        "roles": ["developer", "team_lead"],
                        "projects": [
                            {
                                "id": "proj_001",
                                "name": "StageFlow",
                                "access_level": "admin",
                                "permissions": ["read", "write", "deploy"]
                            }
                        ]
                    }
                }
            ]
        },
        "errors": None,
        "warnings": [
            {
                "code": "WARN_001",
                "message": "Rate limit approaching",
                "details": {
                    "current_usage": 847,
                    "limit": 1000,
                    "reset_time": "2024-01-20T16:00:00Z"
                }
            }
        ]
    }


# Dynamic Data Generation Fixtures
@pytest.fixture
def random_user_generator():
    """Generator function for creating random user data."""
    def _generate_user(
        user_id: str | None = None,
        verified: bool | None = None,
        complete_profile: bool = True
    ) -> dict[str, Any]:
        uid = user_id or f"usr_{random.randint(1000, 9999)}"
        is_verified = verified if verified is not None else random.choice([True, False])

        user = {
            "id": uid,
            "email": f"{uid.lower()}@example.com",
            "username": f"user_{uid.split('_')[1]}",
            "verification": {
                "email_verified": is_verified,
                "phone_verified": random.choice([True, False]),
                "identity_verified": random.choice([True, False])
            },
            "metadata": {
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z"
            }
        }

        if complete_profile:
            user["profile"] = {
                "first_name": f"FirstName{random.randint(1, 100)}",
                "last_name": f"LastName{random.randint(1, 100)}",
                "phone": f"+1-555-{random.randint(1000, 9999)}",
                "timezone": random.choice(["UTC", "America/New_York", "Europe/London"])
            }

        return user

    return _generate_user
