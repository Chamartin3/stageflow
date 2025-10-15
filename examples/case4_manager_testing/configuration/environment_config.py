#!/usr/bin/env python3
"""
Environment-based Configuration Example

This example demonstrates how to configure the StageFlow Manager using environment
variables, which is the recommended approach for different deployment environments.
"""

import os
import tempfile
from pathlib import Path

from stageflow.manager import ManagerConfig, ProcessManager


def environment_config_basic():
    """Demonstrate basic environment-based configuration."""
    print("=== Environment-based Configuration ===\n")

    # 1. Default environment configuration
    print("1. Default environment configuration (no env vars set):")
    default_config = ManagerConfig.from_env()
    print(f"   Processes dir: {default_config.processes_dir}")
    print(f"   Default format: {default_config.default_format}")
    print(f"   Backup enabled: {default_config.backup_enabled}")
    print()

    # 2. Custom environment configuration
    print("2. Custom environment configuration:")

    # Create a temporary directory for this example
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Set custom environment variables
        custom_env = {
            "STAGEFLOW_PROCESSES_DIR": str(temp_path / "custom_processes"),
            "STAGEFLOW_DEFAULT_FORMAT": "json",
            "STAGEFLOW_CREATE_DIR": "true",
            "STAGEFLOW_BACKUP_ENABLED": "true",
            "STAGEFLOW_BACKUP_DIR": str(temp_path / "backups"),
            "STAGEFLOW_MAX_BACKUPS": "25",
            "STAGEFLOW_STRICT_VALIDATION": "false",
            "STAGEFLOW_AUTO_FIX_PERMISSIONS": "true"
        }

        # Apply environment variables temporarily
        original_env = {}
        for key, value in custom_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # Create configuration from environment
            env_config = ManagerConfig.from_env()

            print(f"   Processes dir: {env_config.processes_dir}")
            print(f"   Default format: {env_config.default_format}")
            print(f"   Backup enabled: {env_config.backup_enabled}")
            print(f"   Backup dir: {env_config.backup_dir}")
            print(f"   Max backups: {env_config.max_backups}")
            print(f"   Strict validation: {env_config.strict_validation}")
            print(f"   Auto fix permissions: {env_config.auto_fix_permissions}")
            print()

            # 3. Using environment config with ProcessManager
            print("3. Using environment config with ProcessManager:")
            manager = ProcessManager(env_config)
            processes = manager.list_processes()
            print("   Manager created successfully")
            print(f"   Found processes: {len(processes)}")
            print()

        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


def environment_config_scenarios():
    """Demonstrate different environment configuration scenarios."""
    print("=== Environment Configuration Scenarios ===\n")

    scenarios = [
        {
            "name": "Development Environment",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "./dev_processes",
                "STAGEFLOW_DEFAULT_FORMAT": "yaml",
                "STAGEFLOW_BACKUP_ENABLED": "false",
                "STAGEFLOW_STRICT_VALIDATION": "true"
            }
        },
        {
            "name": "Testing Environment",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/tmp/test_processes",
                "STAGEFLOW_DEFAULT_FORMAT": "json",
                "STAGEFLOW_BACKUP_ENABLED": "true",
                "STAGEFLOW_MAX_BACKUPS": "5",
                "STAGEFLOW_STRICT_VALIDATION": "true"
            }
        },
        {
            "name": "Production Environment",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/var/lib/stageflow/processes",
                "STAGEFLOW_DEFAULT_FORMAT": "yaml",
                "STAGEFLOW_BACKUP_ENABLED": "true",
                "STAGEFLOW_BACKUP_DIR": "/var/lib/stageflow/backups",
                "STAGEFLOW_MAX_BACKUPS": "100",
                "STAGEFLOW_STRICT_VALIDATION": "true",
                "STAGEFLOW_AUTO_FIX_PERMISSIONS": "false"
            }
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}:")

        # Store original environment
        original_env = {}
        for key in scenario['env']:
            original_env[key] = os.environ.get(key)

        # Set scenario environment
        for key, value in scenario['env'].items():
            os.environ[key] = value

        try:
            config = ManagerConfig.from_env()
            print(f"   Processes dir: {config.processes_dir}")
            print(f"   Format: {config.default_format}")
            print(f"   Backup: {config.backup_enabled}")
            if config.backup_enabled:
                print(f"   Max backups: {config.max_backups}")
            print(f"   Strict validation: {config.strict_validation}")

        except Exception as e:
            print(f"   ❌ Configuration failed: {e}")

        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

        print()


def environment_validation():
    """Demonstrate environment configuration validation."""
    print("=== Environment Configuration Validation ===\n")

    # Test various environment configurations
    test_cases = [
        {
            "name": "Valid Configuration",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/tmp/valid_processes",
                "STAGEFLOW_DEFAULT_FORMAT": "yaml"
            },
            "should_pass": True
        },
        {
            "name": "Invalid Format",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/tmp/test_processes",
                "STAGEFLOW_DEFAULT_FORMAT": "xml"  # Invalid format
            },
            "should_pass": True  # Should fallback to YAML
        },
        {
            "name": "Invalid Max Backups",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/tmp/test_processes",
                "STAGEFLOW_MAX_BACKUPS": "-5"  # Negative value
            },
            "should_pass": False
        },
        {
            "name": "Boolean Parsing Variations",
            "env": {
                "STAGEFLOW_PROCESSES_DIR": "/tmp/test_processes",
                "STAGEFLOW_BACKUP_ENABLED": "1",
                "STAGEFLOW_STRICT_VALIDATION": "yes",
                "STAGEFLOW_AUTO_FIX_PERMISSIONS": "false"
            },
            "should_pass": True
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}:")

        # Store and set environment
        original_env = {}
        for key in test_case['env']:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_case['env'][key]

        try:
            config = ManagerConfig.from_env()
            if test_case['should_pass']:
                print("   ✅ Configuration created successfully")
                if 'DEFAULT_FORMAT' in test_case['env']:
                    print(f"   Format: {config.default_format}")
                if 'MAX_BACKUPS' in test_case['env']:
                    print(f"   Max backups: {config.max_backups}")
                if any('BACKUP_ENABLED' in k or 'STRICT_VALIDATION' in k or 'AUTO_FIX' in k
                       for k in test_case['env']):
                    print(f"   Backup: {config.backup_enabled}")
                    print(f"   Strict: {config.strict_validation}")
                    print(f"   Auto fix: {config.auto_fix_permissions}")
            else:
                print("   ❌ Should have failed but didn't")

        except Exception as e:
            if test_case['should_pass']:
                print(f"   ❌ Unexpected failure: {e}")
            else:
                print(f"   ✅ Failed as expected: {e}")

        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

        print()


def custom_prefix_example():
    """Demonstrate custom environment prefix."""
    print("=== Custom Environment Prefix ===\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment variables with custom prefix
        custom_prefix_env = {
            "MYAPP_PROCESSES_DIR": str(Path(temp_dir) / "myapp_processes"),
            "MYAPP_DEFAULT_FORMAT": "json",
            "MYAPP_BACKUP_ENABLED": "true"
        }

        original_env = {}
        for key, value in custom_prefix_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # Create configuration with custom prefix
            config = ManagerConfig.from_env(env_prefix='MYAPP_')

            print("Custom prefix configuration:")
            print(f"   Processes dir: {config.processes_dir}")
            print(f"   Default format: {config.default_format}")
            print(f"   Backup enabled: {config.backup_enabled}")
            print()

        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


def main():
    """Run all environment configuration examples."""
    print("StageFlow Manager Environment Configuration Examples")
    print("=" * 60)
    print()

    try:
        environment_config_basic()
        environment_config_scenarios()
        environment_validation()
        custom_prefix_example()

        print("✅ All environment configuration examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
