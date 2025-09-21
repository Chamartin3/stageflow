"""Mock objects and test doubles for StageFlow testing.

This module provides mock objects, test doubles, and simulated dependencies
for isolated testing of StageFlow components without external dependencies.
"""

import json
from pathlib import Path
from typing import Any

import pytest


# File System Mocks
@pytest.fixture
def mock_file_system():
    """Mock file system operations for testing file-based loaders."""
    class MockFileSystem:
        def __init__(self):
            self.files = {}
            self.directories = set()

        def create_file(self, path: str, content: str):
            """Create a mock file with content."""
            self.files[path] = content
            # Create parent directories
            parent = str(Path(path).parent)
            if parent != '.':
                self.directories.add(parent)

        def read_file(self, path: str) -> str:
            """Read mock file content."""
            if path not in self.files:
                raise FileNotFoundError(f"File not found: {path}")
            return self.files[path]

        def exists(self, path: str) -> bool:
            """Check if mock file or directory exists."""
            return path in self.files or path in self.directories

        def is_file(self, path: str) -> bool:
            """Check if path is a mock file."""
            return path in self.files

        def is_directory(self, path: str) -> bool:
            """Check if path is a mock directory."""
            return path in self.directories

        def list_files(self, directory: str, pattern: str = "*") -> list[str]:
            """List mock files in directory matching pattern."""
            files = []
            for file_path in self.files:
                if file_path.startswith(directory):
                    files.append(file_path)
            return files

    return MockFileSystem()


@pytest.fixture
def temp_process_files(tmp_path):
    """Create temporary process files for testing file loaders."""
    # Create YAML process file
    yaml_content = """
process:
  name: test_process
  description: Test process for file loading
  version: 1.0
  initial_stage: start
  final_stage: end
  stages:
    - name: start
      description: Starting stage
      gates:
        - name: basic_gate
          logic: AND
          locks:
            - property_path: "field1"
              lock_type: "exists"
      transitions:
        - target_stage: end
          condition: basic_gate
    - name: end
      description: Final stage
      gates: []
      transitions: []
"""

    yaml_file = tmp_path / "test_process.yaml"
    yaml_file.write_text(yaml_content)

    # Create JSON process file
    json_content = {
        "process": {
            "name": "test_process_json",
            "description": "Test process in JSON format",
            "version": "1.0",
            "initial_stage": "start",
            "final_stage": "end",
            "stages": [
                {
                    "name": "start",
                    "description": "Starting stage",
                    "gates": [
                        {
                            "name": "basic_gate",
                            "logic": "AND",
                            "locks": [
                                {
                                    "property_path": "field1",
                                    "lock_type": "exists"
                                }
                            ]
                        }
                    ],
                    "transitions": [
                        {
                            "target_stage": "end",
                            "condition": "basic_gate"
                        }
                    ]
                },
                {
                    "name": "end",
                    "description": "Final stage",
                    "gates": [],
                    "transitions": []
                }
            ]
        }
    }

    json_file = tmp_path / "test_process.json"
    json_file.write_text(json.dumps(json_content, indent=2))

    # Create invalid files for error testing
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("invalid: yaml: content: [unclosed")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text('{"invalid": "json", "missing": }')

    return {
        "yaml_file": str(yaml_file),
        "json_file": str(json_file),
        "invalid_yaml": str(invalid_yaml),
        "invalid_json": str(invalid_json),
        "temp_dir": str(tmp_path)
    }


# Database Mocks
@pytest.fixture
def mock_database():
    """Mock database for testing data persistence."""
    class MockDatabase:
        def __init__(self):
            self.data = {}
            self.transaction_active = False
            self.call_log = []

        def connect(self):
            """Mock database connection."""
            self.call_log.append("connect")
            return self

        def disconnect(self):
            """Mock database disconnection."""
            self.call_log.append("disconnect")

        def begin_transaction(self):
            """Begin mock transaction."""
            self.transaction_active = True
            self.call_log.append("begin_transaction")

        def commit(self):
            """Commit mock transaction."""
            self.transaction_active = False
            self.call_log.append("commit")

        def rollback(self):
            """Rollback mock transaction."""
            self.transaction_active = False
            self.call_log.append("rollback")

        def execute(self, query: str, params: dict = None):
            """Execute mock query."""
            self.call_log.append(f"execute: {query}")
            return {"rows_affected": 1, "query": query, "params": params}

        def fetch_one(self, table: str, conditions: dict = None):
            """Fetch single record from mock table."""
            key = f"{table}:{conditions}"
            self.call_log.append(f"fetch_one: {key}")
            return self.data.get(key)

        def fetch_all(self, table: str, conditions: dict = None):
            """Fetch all records from mock table."""
            self.call_log.append(f"fetch_all: {table}")
            return [v for k, v in self.data.items() if k.startswith(table)]

        def insert(self, table: str, data: dict):
            """Insert data into mock table."""
            key = f"{table}:{data.get('id', len(self.data))}"
            self.data[key] = data
            self.call_log.append(f"insert: {key}")
            return {"id": data.get("id", len(self.data))}

        def update(self, table: str, data: dict, conditions: dict):
            """Update data in mock table."""
            key = f"{table}:{conditions}"
            if key in self.data:
                self.data[key].update(data)
            self.call_log.append(f"update: {key}")

        def delete(self, table: str, conditions: dict):
            """Delete data from mock table."""
            key = f"{table}:{conditions}"
            if key in self.data:
                del self.data[key]
            self.call_log.append(f"delete: {key}")

    return MockDatabase()


# Network Mocks
@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing external API interactions."""
    class MockResponse:
        def __init__(self, json_data: dict, status_code: int = 200, headers: dict = None):
            self.json_data = json_data
            self.status_code = status_code
            self.headers = headers or {}
            self.text = json.dumps(json_data)

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code} Error")

    class MockHttpClient:
        def __init__(self):
            self.responses = {}
            self.call_log = []
            self.default_response = MockResponse({"error": "Not mocked"}, 404)

        def set_response(self, url: str, response_data: dict, status_code: int = 200):
            """Set mock response for a specific URL."""
            self.responses[url] = MockResponse(response_data, status_code)

        def get(self, url: str, headers: dict = None, params: dict = None):
            """Mock GET request."""
            self.call_log.append(f"GET: {url}")
            return self.responses.get(url, self.default_response)

        def post(self, url: str, json: dict = None, headers: dict = None):
            """Mock POST request."""
            self.call_log.append(f"POST: {url}")
            return self.responses.get(url, MockResponse({"created": True}, 201))

        def put(self, url: str, json: dict = None, headers: dict = None):
            """Mock PUT request."""
            self.call_log.append(f"PUT: {url}")
            return self.responses.get(url, MockResponse({"updated": True}, 200))

        def delete(self, url: str, headers: dict = None):
            """Mock DELETE request."""
            self.call_log.append(f"DELETE: {url}")
            return self.responses.get(url, MockResponse({"deleted": True}, 204))

    return MockHttpClient()


# External Service Mocks
@pytest.fixture
def mock_email_service():
    """Mock email service for testing notifications."""
    class MockEmailService:
        def __init__(self):
            self.sent_emails = []
            self.fail_next = False

        def send_email(self, to: str, subject: str, body: str, from_addr: str = None):
            """Send mock email."""
            if self.fail_next:
                self.fail_next = False
                raise Exception("Email service unavailable")

            email = {
                "to": to,
                "subject": subject,
                "body": body,
                "from": from_addr or "noreply@stageflow.dev",
                "timestamp": "2024-01-20T15:30:00Z"
            }
            self.sent_emails.append(email)
            return {"message_id": f"msg_{len(self.sent_emails)}"}

        def send_template_email(self, to: str, template_id: str, variables: dict):
            """Send email using template."""
            email = {
                "to": to,
                "template_id": template_id,
                "variables": variables,
                "timestamp": "2024-01-20T15:30:00Z"
            }
            self.sent_emails.append(email)
            return {"message_id": f"tmpl_{len(self.sent_emails)}"}

        def set_fail_next(self):
            """Make next email send fail."""
            self.fail_next = True

    return MockEmailService()


@pytest.fixture
def mock_payment_processor():
    """Mock payment processor for testing financial workflows."""
    class MockPaymentProcessor:
        def __init__(self):
            self.transactions = []
            self.fail_next = False
            self.balance = 10000.0

        def process_payment(self, amount: float, payment_method: dict, order_id: str):
            """Process mock payment."""
            if self.fail_next:
                self.fail_next = False
                return {
                    "success": False,
                    "error": "Payment declined",
                    "transaction_id": None
                }

            if amount > self.balance:
                return {
                    "success": False,
                    "error": "Insufficient funds",
                    "transaction_id": None
                }

            transaction_id = f"txn_{len(self.transactions) + 1:06d}"
            transaction = {
                "transaction_id": transaction_id,
                "amount": amount,
                "payment_method": payment_method,
                "order_id": order_id,
                "status": "completed",
                "timestamp": "2024-01-20T15:30:00Z"
            }
            self.transactions.append(transaction)
            self.balance -= amount

            return {
                "success": True,
                "transaction_id": transaction_id,
                "amount_charged": amount
            }

        def refund_payment(self, transaction_id: str, amount: float = None):
            """Process mock refund."""
            transaction = next(
                (t for t in self.transactions if t["transaction_id"] == transaction_id),
                None
            )

            if not transaction:
                return {"success": False, "error": "Transaction not found"}

            refund_amount = amount or transaction["amount"]
            self.balance += refund_amount

            return {
                "success": True,
                "refund_id": f"ref_{len(self.transactions)}",
                "amount_refunded": refund_amount
            }

        def set_fail_next(self):
            """Make next payment fail."""
            self.fail_next = True

    return MockPaymentProcessor()


# Configuration Mocks
@pytest.fixture
def mock_config():
    """Mock configuration for testing different settings."""
    class MockConfig:
        def __init__(self):
            self.config = {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "test_db",
                    "user": "test_user"
                },
                "email": {
                    "provider": "mock",
                    "api_key": "test_key"
                },
                "security": {
                    "secret_key": "test_secret",
                    "token_expiry": 3600
                },
                "features": {
                    "advanced_validation": True,
                    "async_processing": False,
                    "caching": True
                }
            }

        def get(self, key: str, default: Any = None):
            """Get configuration value by dot notation."""
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value

        def set(self, key: str, value: Any):
            """Set configuration value by dot notation."""
            keys = key.split(".")
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value

        def update(self, updates: dict):
            """Update configuration with new values."""
            self.config.update(updates)

    return MockConfig()


# Logger Mocks
@pytest.fixture
def mock_logger():
    """Mock logger for testing logging behavior."""
    class MockLogger:
        def __init__(self):
            self.logs = []

        def debug(self, message: str, **kwargs):
            self.logs.append({"level": "debug", "message": message, "kwargs": kwargs})

        def info(self, message: str, **kwargs):
            self.logs.append({"level": "info", "message": message, "kwargs": kwargs})

        def warning(self, message: str, **kwargs):
            self.logs.append({"level": "warning", "message": message, "kwargs": kwargs})

        def error(self, message: str, **kwargs):
            self.logs.append({"level": "error", "message": message, "kwargs": kwargs})

        def critical(self, message: str, **kwargs):
            self.logs.append({"level": "critical", "message": message, "kwargs": kwargs})

        def get_logs(self, level: str = None):
            """Get logs, optionally filtered by level."""
            if level:
                return [log for log in self.logs if log["level"] == level]
            return self.logs

        def clear(self):
            """Clear all logs."""
            self.logs = []

    return MockLogger()


# Event System Mocks
@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing event-driven functionality."""
    class MockEventBus:
        def __init__(self):
            self.events = []
            self.subscribers = {}

        def publish(self, event_type: str, data: dict):
            """Publish mock event."""
            event = {
                "type": event_type,
                "data": data,
                "timestamp": "2024-01-20T15:30:00Z"
            }
            self.events.append(event)

            # Notify subscribers
            for callback in self.subscribers.get(event_type, []):
                callback(event)

        def subscribe(self, event_type: str, callback):
            """Subscribe to mock events."""
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(callback)

        def unsubscribe(self, event_type: str, callback):
            """Unsubscribe from mock events."""
            if event_type in self.subscribers:
                self.subscribers[event_type].remove(callback)

        def get_events(self, event_type: str = None):
            """Get events, optionally filtered by type."""
            if event_type:
                return [event for event in self.events if event["type"] == event_type]
            return self.events

        def clear(self):
            """Clear all events."""
            self.events = []

    return MockEventBus()


# Cache Mocks
@pytest.fixture
def mock_cache():
    """Mock cache for testing caching behavior."""
    class MockCache:
        def __init__(self):
            self.data = {}
            self.access_log = []

        def get(self, key: str):
            """Get value from mock cache."""
            self.access_log.append(f"get: {key}")
            return self.data.get(key)

        def set(self, key: str, value: Any, ttl: int = None):
            """Set value in mock cache."""
            self.access_log.append(f"set: {key}")
            self.data[key] = value

        def delete(self, key: str):
            """Delete value from mock cache."""
            self.access_log.append(f"delete: {key}")
            if key in self.data:
                del self.data[key]

        def clear(self):
            """Clear mock cache."""
            self.access_log.append("clear")
            self.data = {}

        def exists(self, key: str) -> bool:
            """Check if key exists in mock cache."""
            self.access_log.append(f"exists: {key}")
            return key in self.data

        def keys(self) -> list[str]:
            """Get all cache keys."""
            self.access_log.append("keys")
            return list(self.data.keys())

    return MockCache()


# Performance Testing Mocks
@pytest.fixture
def mock_performance_monitor():
    """Mock performance monitor for testing performance tracking."""
    class MockPerformanceMonitor:
        def __init__(self):
            self.metrics = {}
            self.timers = {}

        def start_timer(self, name: str):
            """Start performance timer."""
            self.timers[name] = "2024-01-20T15:30:00Z"

        def end_timer(self, name: str):
            """End performance timer and record metric."""
            if name in self.timers:
                self.metrics[name] = 0.150  # Mock 150ms execution time
                del self.timers[name]

        def record_metric(self, name: str, value: float, unit: str = "ms"):
            """Record performance metric."""
            self.metrics[name] = {"value": value, "unit": unit}

        def get_metrics(self):
            """Get all recorded metrics."""
            return self.metrics

        def clear(self):
            """Clear all metrics."""
            self.metrics = {}
            self.timers = {}

    return MockPerformanceMonitor()
