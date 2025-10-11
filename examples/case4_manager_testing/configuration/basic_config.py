#!/usr/bin/env python3
"""
Basic Manager Configuration Example

This example demonstrates basic configuration patterns for the StageFlow Manager,
including creating configurations programmatically and using them with the ProcessManager.
"""

import tempfile
from pathlib import Path
from stageflow.manager import ManagerConfig, ProcessManager, ProcessFileFormat


def basic_configuration_example():
    """Demonstrate basic manager configuration."""
    print("=== Basic Manager Configuration Example ===\n")

    # Create a temporary directory for this example
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 1. Basic configuration with minimal settings
        print("1. Creating basic configuration...")
        basic_config = ManagerConfig(
            processes_dir=temp_path / "processes",
            default_format=ProcessFileFormat.YAML,
            create_dir_if_missing=True
        )

        print(f"   Processes directory: {basic_config.processes_dir}")
        print(f"   Default format: {basic_config.default_format}")
        print(f"   Directory created: {basic_config.processes_dir.exists()}")
        print()

        # 2. Configuration with backup settings
        print("2. Creating configuration with backups enabled...")
        backup_config = ManagerConfig(
            processes_dir=temp_path / "processes_with_backup",
            default_format=ProcessFileFormat.YAML,
            create_dir_if_missing=True,
            backup_enabled=True,
            backup_dir=temp_path / "backups",
            max_backups=10
        )

        print(f"   Processes directory: {backup_config.processes_dir}")
        print(f"   Backup enabled: {backup_config.backup_enabled}")
        print(f"   Backup directory: {backup_config.backup_dir}")
        print(f"   Max backups: {backup_config.max_backups}")
        print()

        # 3. Configuration with different format
        print("3. Creating configuration with JSON format...")
        json_config = ManagerConfig(
            processes_dir=temp_path / "json_processes",
            default_format=ProcessFileFormat.JSON,
            create_dir_if_missing=True,
            strict_validation=False
        )

        print(f"   Default format: {json_config.default_format}")
        print(f"   Strict validation: {json_config.strict_validation}")
        print()

        # 4. Using configurations with ProcessManager
        print("4. Using configurations with ProcessManager...")

        # Create managers with different configs
        basic_manager = ProcessManager(basic_config)
        backup_manager = ProcessManager(backup_config)
        json_manager = ProcessManager(json_config)

        # Show that each manager uses its configuration
        print(f"   Basic manager processes: {len(basic_manager.list_processes())}")
        print(f"   Backup manager processes: {len(backup_manager.list_processes())}")
        print(f"   JSON manager processes: {len(json_manager.list_processes())}")
        print()

        # 5. Configuration validation
        print("5. Configuration validation...")
        print(f"   Basic config valid: {basic_config.is_valid_processes_dir()}")
        print(f"   Backup config valid: {backup_config.is_valid_processes_dir()}")
        print(f"   JSON config valid: {json_config.is_valid_processes_dir()}")
        print()

        # 6. Configuration serialization
        print("6. Configuration serialization...")
        config_dict = basic_config.to_dict()
        print(f"   Config as dict keys: {list(config_dict.keys())}")

        # Recreate config from dict
        recreated_config = ManagerConfig.from_dict(config_dict)
        print(f"   Recreated config processes_dir: {recreated_config.processes_dir}")
        print(f"   Configs are equivalent: {basic_config.processes_dir == recreated_config.processes_dir}")
        print()


def file_path_examples():
    """Demonstrate file path generation and format handling."""
    print("=== File Path and Format Examples ===\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create configs with different formats
        yaml_config = ManagerConfig(
            processes_dir=temp_path,
            default_format=ProcessFileFormat.YAML
        )

        json_config = ManagerConfig(
            processes_dir=temp_path,
            default_format=ProcessFileFormat.JSON
        )

        auto_config = ManagerConfig(
            processes_dir=temp_path,
            default_format=ProcessFileFormat.AUTO
        )

        # Generate file paths for different formats
        process_name = "test_process"

        print("1. File path generation for different formats:")
        yaml_path = yaml_config.get_process_file_path(process_name)
        json_path = json_config.get_process_file_path(process_name)
        auto_path = auto_config.get_process_file_path(process_name)

        print(f"   YAML format: {yaml_path}")
        print(f"   JSON format: {json_path}")
        print(f"   AUTO format: {auto_path}")
        print()

        # Create actual files to test AUTO format detection
        print("2. AUTO format detection:")

        # Create a YAML file
        yaml_file = temp_path / f"{process_name}.yaml"
        yaml_file.write_text("name: test\nstages: {}")

        # Now AUTO format should detect the YAML file
        auto_detected_path = auto_config.get_process_file_path(process_name)
        print(f"   AUTO detected path: {auto_detected_path}")
        print(f"   Detected YAML file: {auto_detected_path == yaml_file}")
        print()

        # 3. Backup path generation
        backup_config = ManagerConfig(
            processes_dir=temp_path,
            backup_enabled=True,
            backup_dir=temp_path / "backups"
        )

        print("3. Backup path generation:")
        backup_path = backup_config.get_backup_path(process_name, "20241201_120000")
        print(f"   Backup path: {backup_path}")
        print(f"   Backup dir exists: {backup_config.backup_dir.exists()}")
        print()


def configuration_comparison():
    """Compare different configuration approaches."""
    print("=== Configuration Approaches Comparison ===\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 1. Minimal configuration
        minimal = ManagerConfig(processes_dir=temp_path)

        # 2. Development configuration
        development = ManagerConfig(
            processes_dir=temp_path / "dev_processes",
            default_format=ProcessFileFormat.YAML,
            create_dir_if_missing=True,
            backup_enabled=False,
            strict_validation=True
        )

        # 3. Production configuration
        production = ManagerConfig(
            processes_dir=temp_path / "prod_processes",
            default_format=ProcessFileFormat.JSON,
            create_dir_if_missing=True,
            backup_enabled=True,
            backup_dir=temp_path / "prod_backups",
            max_backups=50,
            strict_validation=True,
            auto_fix_permissions=False
        )

        configs = {
            "Minimal": minimal,
            "Development": development,
            "Production": production
        }

        print("Configuration comparison:")
        for name, config in configs.items():
            print(f"\n{name} Configuration:")
            print(f"  - Processes dir: {config.processes_dir.name}")
            print(f"  - Format: {config.default_format}")
            print(f"  - Backup enabled: {config.backup_enabled}")
            print(f"  - Strict validation: {config.strict_validation}")
            print(f"  - Auto fix permissions: {config.auto_fix_permissions}")
            if config.backup_enabled:
                print(f"  - Max backups: {config.max_backups}")


def main():
    """Run all configuration examples."""
    print("StageFlow Manager Configuration Examples")
    print("=" * 50)
    print()

    try:
        basic_configuration_example()
        file_path_examples()
        configuration_comparison()

        print("✅ All configuration examples completed successfully!")

    except Exception as e:
        print(f"❌ Example failed with error: {e}")
        raise


if __name__ == "__main__":
    main()