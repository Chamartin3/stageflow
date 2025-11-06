"""Registry management commands."""

import shutil
from pathlib import Path
from typing import Annotated

import typer

from stageflow.cli.utils import ProcessFormatter
from stageflow.loader import ProcessLoader
from stageflow.manager import ManagerConfig, ProcessRegistry

# Create registry subcommand group
reg_app = typer.Typer(
    name="reg",
    help="Registry management commands",
    no_args_is_help=True,
)


@reg_app.command(name="list")
def list_processes(
    ctx: typer.Context,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """List all processes in the registry."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        processes = registry.list_processes()

        # Build process details for all processes
        loader = ProcessLoader()
        process_details = []
        for process_name in processes:
            try:
                process_file_path = registry.get_process_file_path(process_name)
                if process_file_path:
                    # Use ProcessLoader for consistent error handling
                    result = loader.load(process_file_path)
                    if result.success and result.process is not None:
                        process = result.process
                    else:
                        # Process load failed - add error detail
                        process_details.append(
                            {
                                "registry_name": process_name,
                                "error": f"Failed to load: {result.get_error_summary()}",
                                "valid": False,
                            }
                        )
                        continue
                else:
                    process = registry.load_process(process_name)

                description = ProcessFormatter.build_description(process)
                # Create mutable dict with additional field
                detail = dict(description)
                detail["registry_name"] = process_name
                process_details.append(detail)
            except Exception as e:
                process_details.append(
                    {
                        "registry_name": process_name,
                        "error": f"Failed to load: {str(e)}",
                        "valid": False,
                    }
                )

        # Print registry list (handles JSON vs normal mode and formatting)
        cli_ctx.printer.print_registry_list(
            processes=processes,
            registry_dir=str(config.processes_dir),
            process_details=process_details,
        )

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Failed to list registry processes: {e}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1) from e


@reg_app.command(name="import")
def import_process(
    ctx: typer.Context,
    file_path: Annotated[Path, typer.Argument(help="Process file to import")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Registry name (defaults to filename)"),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing process")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Import a process file into the registry."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    # Validate file exists
    if not file_path.exists():
        error_msg = f"File '{file_path}' not found"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1)

    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        # Determine registry name
        registry_name = name if name else file_path.stem

        # Check if process already exists
        if registry.process_exists(registry_name) and not force:
            error_msg = (
                f"Process '@{registry_name}' already exists in registry. "
                f"Use --force to overwrite."
            )
            if json_output:
                cli_ctx.print_json(data={"error": error_msg, "exists": True})
            else:
                cli_ctx.print_error(error_msg)
            raise typer.Exit(1)

        # Load process to validate it using ProcessLoader
        cli_ctx.print_progress(f"Importing process from {file_path}...")
        loader = ProcessLoader()
        result = loader.load(str(file_path))

        if not result.success or result.process is None:
            # Use structured error reporting from ProcessLoader
            cli_ctx.printer.print_load_result(result, json_mode=json_output)
            raise typer.Exit(1)

        process = result.process

        # Determine if overwriting
        is_overwrite = registry.process_exists(registry_name) and force

        # Save to registry
        registry.save_process(registry_name, process)

        # Print success (handles JSON vs normal mode and formatting)
        cli_ctx.printer.print_registry_import_success(
            registry_name=registry_name,
            source_file=str(file_path),
            overwritten=is_overwrite,
        )

    except typer.Exit:
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Failed to import process: {e}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1) from e


@reg_app.command(name="export")
def export_process(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Registry process name (without @)")],
    file_path: Annotated[Path, typer.Argument(help="Destination file path")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Export a registry process to a file."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        # Get source file
        source_path = registry.get_process_file_path(name)
        if not source_path or not source_path.exists():
            error_msg = f"Process '{name}' not found in registry"
            if json_output:
                cli_ctx.print_json(data={"error": error_msg})
            else:
                cli_ctx.print_error(error_msg)
            raise typer.Exit(1)

        # Copy file
        cli_ctx.print_progress(f"Exporting process '@{name}' to {file_path}...")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, file_path)

        # Print success (handles JSON vs normal mode and formatting)
        cli_ctx.printer.print_registry_export_success(
            registry_name=name,
            destination_file=str(file_path),
        )

    except typer.Exit:
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Failed to export process: {e}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1) from e


@reg_app.command(name="delete")
def delete_process(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Registry process name (without @)")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Delete a process from the registry."""
    # Access CLI context
    cli_ctx = ctx.obj

    # Set JSON mode
    cli_ctx.json_mode = json_output
    cli_ctx.printer.json_mode = json_output

    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        # Check if process exists
        process_file_path = registry.get_process_file_path(name)
        if not process_file_path:
            error_msg = f"Process '{name}' not found in registry"
            if json_output:
                cli_ctx.print_json(data={"error": error_msg})
            else:
                cli_ctx.print_error(error_msg)
            raise typer.Exit(1)

        # Confirm deletion (unless forced or JSON mode)
        if not json_output and not force:
            confirmed = typer.confirm(
                f"Are you sure you want to delete process '{name}' from the registry?",
                default=False,
            )
            if not confirmed:
                cli_ctx.console.print("Deletion cancelled.")
                return

        # Delete process
        cli_ctx.print_progress(f"Deleting process '@{name}' from registry...")
        registry.delete_process(name, create_backup=True)

        # Print success (handles JSON vs normal mode and formatting)
        cli_ctx.printer.print_registry_delete_success(
            registry_name=name,
            file_path=str(process_file_path),
        )

    except typer.Exit:
        raise
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Failed to delete process: {e}"
        if json_output:
            cli_ctx.print_json(data={"error": error_msg})
        else:
            cli_ctx.print_error(error_msg)
        raise typer.Exit(1) from e
