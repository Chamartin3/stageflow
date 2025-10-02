"""
Tests for intermediate example processes.

This module validates that intermediate complexity example processes
work correctly and handle complex business logic appropriately.
"""

from pathlib import Path

import pytest

from stageflow import Element, load_process
from stageflow.process.result import EvaluationState


class TestECommerceOrderExample:
    """Test the e-commerce order fulfillment intermediate example."""

    @pytest.fixture
    def process(self):
        """Load the e-commerce order process."""
        examples_dir = Path(__file__).parent.parent.parent / "stageflow" / "examples"
        process_file = examples_dir / "intermediate" / "processes" / "ecommerce_order.yaml"
        return load_process(process_file)

    def test_new_order_awaits_payment(self, process):
        """Test that new orders await payment processing."""
        order_data = {
            "order_id": "ORD-2024-002",
            "customer_id": "CUST-23456",
            "items": [
                {
                    "product_id": "BOOK-001",
                    "name": "Programming Guide",
                    "quantity": 2,
                    "unit_price": 39.99
                }
            ],
            "total_amount": 79.98,
            "shipping_address": {
                "street": "456 Oak Ave",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62701",
                "country": "USA"
            }
            # Missing payment information
        }
        element = Element(order_data)
        result = process.evaluate(element)

        assert result.current_stage == "order_placed"
        assert result.state == EvaluationState.AWAITING
        assert not result.can_advance

    def test_payment_amount_mismatch_awaiting(self, process):
        """Test that payment amount mismatch keeps order awaiting."""
        order_data = {
            "order_id": "ORD-2024-003",
            "customer_id": "CUST-34567",
            "items": [
                {
                    "product_id": "SHIRT-001",
                    "name": "Cotton T-Shirt",
                    "quantity": 3,
                    "unit_price": 24.99
                }
            ],
            "total_amount": 74.97,
            "shipping_address": {
                "street": "789 Pine Rd",
                "city": "Portland",
                "state": "OR",
                "zip_code": "97201",
                "country": "USA"
            },
            "payment": {
                "method": "credit_card",
                "amount": 50.00,  # Insufficient amount
                "authorization_code": "AUTH-234567"
            }
        }
        element = Element(order_data)
        result = process.evaluate(element)

        assert result.current_stage == "order_placed"
        assert result.state == EvaluationState.AWAITING

    def test_order_being_fulfilled(self, process):
        """Test order in fulfillment process."""
        order_data = {
            "order_id": "ORD-2024-005",
            "customer_id": "CUST-56789",
            "items": [
                {
                    "product_id": "HEADPHONES-001",
                    "name": "Bluetooth Headphones",
                    "quantity": 1,
                    "unit_price": 149.99
                }
            ],
            "total_amount": 149.99,
            "shipping_address": {
                "street": "654 Maple Dr",
                "city": "Austin",
                "state": "TX",
                "zip_code": "73301",
                "country": "USA"
            },
            "payment": {
                "method": "paypal",
                "amount": 149.99,
                "authorization_code": "AUTH-456789",
                "processed_at": "2024-01-15T12:00:00Z"
            },
            "inventory": {
                "availability": [
                    {
                        "product_id": "HEADPHONES-001",
                        "available": True
                    }
                ],
                "quantities": [
                    {
                        "product_id": "HEADPHONES-001",
                        "available_quantity": 25,
                        "reserved_quantity": 1
                    }
                ],
                "reserved_at": "2024-01-15T12:05:00Z"
            },
            "fulfillment": {
                "picked_at": "2024-01-16T10:00:00Z"
                # Missing packed_at and shipping info
            }
        }
        element = Element(order_data)
        result = process.evaluate(element)

        assert result.current_stage == "inventory_reserved"
        assert result.state == EvaluationState.FULFILLING

    def test_successful_order_completion(self, process):
        """Test successfully completed order."""
        order_data = {
            "order_id": "ORD-2024-001",
            "customer_id": "CUST-12345",
            "items": [
                {
                    "product_id": "LAPTOP-001",
                    "name": "Gaming Laptop",
                    "quantity": 1,
                    "unit_price": 1299.99
                },
                {
                    "product_id": "MOUSE-001",
                    "name": "Wireless Mouse",
                    "quantity": 1,
                    "unit_price": 29.99
                }
            ],
            "total_amount": 1329.98,
            "shipping_address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "12345",
                "country": "USA"
            },
            "payment": {
                "method": "credit_card",
                "amount": 1329.98,
                "authorization_code": "AUTH-123456",
                "transaction_id": "TXN-789012",
                "processed_at": "2024-01-15T10:30:00Z"
            },
            "inventory": {
                "availability": [
                    {"product_id": "LAPTOP-001", "available": True},
                    {"product_id": "MOUSE-001", "available": True}
                ],
                "quantities": [
                    {
                        "product_id": "LAPTOP-001",
                        "available_quantity": 10,
                        "reserved_quantity": 1
                    },
                    {
                        "product_id": "MOUSE-001",
                        "available_quantity": 50,
                        "reserved_quantity": 1
                    }
                ],
                "reserved_at": "2024-01-15T10:35:00Z"
            },
            "fulfillment": {
                "picked_at": "2024-01-16T09:00:00Z",
                "packed_at": "2024-01-16T10:30:00Z",
                "warehouse_location": "WH-WEST"
            },
            "shipping": {
                "tracking_number": "TRK-1234567890",
                "carrier": "FedEx",
                "service_level": "Ground",
                "shipped_at": "2024-01-16T14:00:00Z",
                "delivered_at": "2024-01-18T16:30:00Z",
                "delivery_status": "delivered"
            }
        }
        element = Element(order_data)
        result = process.evaluate(element)

        assert result.current_stage == "order_delivered"
        assert result.state == EvaluationState.COMPLETED
        assert not result.can_advance

    def test_cancelled_order_final_state(self, process):
        """Test cancelled order reaches final state."""
        order_data = {
            "order_id": "ORD-2024-008",
            "customer_id": "CUST-89012",
            "cancellation_reason": "Customer requested cancellation",
            "status": "cancelled",
            "cancelled_at": "2024-01-15T16:00:00Z",
            "refund_processed": True,
            "refund_amount": 199.99
        }
        element = Element(order_data)
        result = process.evaluate(element)

        assert result.current_stage == "order_cancelled"
        assert result.state == EvaluationState.COMPLETED


class TestDocumentApprovalExample:
    """Test the document approval workflow intermediate example."""

    @pytest.fixture
    def process(self):
        """Load the document approval process."""
        examples_dir = Path(__file__).parent.parent.parent / "stageflow" / "examples"
        process_file = examples_dir / "intermediate" / "processes" / "document_approval.yaml"
        return load_process(process_file)

    def test_new_document_awaits_assignment(self, process):
        """Test that new documents await reviewer assignment."""
        document_data = {
            "document_id": "DOC-2024-001",
            "title": "New Employee Handbook",
            "author_id": "AUTHOR-123",
            "document_type": "policy",
            "content_summary": "Updated employee handbook with new policies",
            "urgency_level": "normal",
            "business_justification": "Update required for compliance",
            "estimated_impact": "medium"
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "document_submitted"
        assert result.state == EvaluationState.AWAITING

    def test_document_under_review(self, process):
        """Test document in review state."""
        document_data = {
            "document_id": "DOC-2024-002",
            "title": "Security Procedure Update",
            "author_id": "AUTHOR-456",
            "document_type": "procedure",
            "content_summary": "Updated security procedures for remote work",
            "content": {
                "document_url": "https://docs.company.com/doc-123"
            },
            "metadata": {
                "author_id": "AUTHOR-456",
                "department": "IT Security",
                "creation_date": "2024-01-15"
            },
            "workflow": {
                "primary_reviewer_id": "REVIEWER-789",
                "assigned_at": "2024-01-15T10:00:00Z"
            }
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "under_review"
        assert result.state == EvaluationState.AWAITING

    def test_document_pending_approval(self, process):
        """Test document that passed review and is pending approval."""
        document_data = {
            "document_id": "DOC-2024-003",
            "title": "HR Policy Update",
            "author_id": "AUTHOR-789",
            "document_type": "policy",
            "content_summary": "Updated HR policies for 2024",
            "workflow": {
                "primary_reviewer_id": "REVIEWER-123",
                "manager_id": "MANAGER-456"
            },
            "review": {
                "completed_at": "2024-01-16T14:00:00Z",
                "decision": "approve",
                "comments": "Document looks good, ready for manager approval"
            }
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "pending_approval"
        assert result.state == EvaluationState.AWAITING

    def test_manager_approved_document(self, process):
        """Test document approved by manager."""
        document_data = {
            "document_id": "DOC-2024-004",
            "title": "Procedure Manual",
            "author_id": "AUTHOR-101",
            "document_type": "procedure",
            "content_summary": "Updated procedure manual",
            "workflow": {
                "primary_reviewer_id": "REVIEWER-123",
                "manager_id": "MANAGER-456"
            },
            "review": {
                "completed_at": "2024-01-16T14:00:00Z",
                "decision": "approve",
                "comments": "Reviewed and approved"
            },
            "manager_review": {
                "completed_at": "2024-01-17T10:00:00Z",
                "decision": "approve",
                "signature": "MANAGER-456-SIG",
                "comments": "Approved for implementation"
            },
            "final_approval": {
                "approved_at": "2024-01-17T10:00:00Z",
                "approved_by": "MANAGER-456"
            },
            "status": "approved"
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "document_approved"
        assert result.state == EvaluationState.COMPLETED

    def test_document_rejected(self, process):
        """Test rejected document reaches final state."""
        document_data = {
            "document_id": "DOC-2024-005",
            "title": "Rejected Document",
            "author_id": "AUTHOR-202",
            "rejection_reason": "Does not meet quality standards",
            "status": "rejected",
            "rejected_at": "2024-01-16T15:00:00Z"
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "document_rejected"
        assert result.state == EvaluationState.COMPLETED

    def test_document_awaiting_changes(self, process):
        """Test document waiting for author changes."""
        document_data = {
            "document_id": "DOC-2024-006",
            "title": "Document Needing Changes",
            "author_id": "AUTHOR-303",
            "document_type": "guideline",
            "review": {
                "completed_at": "2024-01-16T12:00:00Z",
                "decision": "request_changes",
                "comments": "Please address formatting issues and add more examples"
            },
            "change_requests": {
                "items": [
                    "Fix formatting in section 3",
                    "Add more practical examples",
                    "Update references section"
                ],
                "requested_at": "2024-01-16T12:00:00Z"
            }
        }
        element = Element(document_data)
        result = process.evaluate(element)

        assert result.current_stage == "awaiting_changes"
        assert result.state == EvaluationState.AWAITING
