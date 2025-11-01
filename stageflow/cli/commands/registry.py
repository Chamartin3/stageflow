"""Registry management commands."""

import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from stageflow.cli.utils import build_process_description, show_success
from stageflow.manager import ManagerConfig, ProcessRegistry
from stageflow.schema import ProcessWithErrors, load_process, load_process_graceful

console = Console()

# Create registry subcommand group
reg_app = typer.Typer(
    name="reg",
    help="Registry management commands",
    no_args_is_help=True,
)


@reg_app.command(name="list")
def list_processes(
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """List all processes in the registry."""
    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        processes = registry.list_processes()

        if json_output:
            process_details = []
            for process_name in processes:
                try:
                    process = registry.load_process(process_name)
                    description = build_process_description(process)
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

            result = {
                "registry_processes": process_details,
                "total_count": len(processes),
            }
            console.print_json(data=result)
        else:
            if not processes:
                console.print("📂 No processes found in registry")
                console.print(f"   Registry directory: {config.processes_dir}")
                console.print(
                    "   Use 'stageflow reg import' to add processes to registry"
                )
                return

            console.print(
                f"[bold]📂 Registry Processes ({len(processes)} found)[/bold]"
            )
            console.print(f"   Registry directory: {config.processes_dir}\n")

            for i, process_name in enumerate(sorted(processes)):
                try:
                    process_file_path = registry.get_process_file_path(process_name)
                    if process_file_path:
                        process = load_process_graceful(process_file_path)
                    else:
                        process = registry.load_process(process_name)

                    description = build_process_description(process)

                    prefix = "└─" if i == len(processes) - 1 else "├─"
                    status_icon = "✅" if description["valid"] else "❌"

                    console.print(f"{prefix} {status_icon} @{process_name}")
                    console.print(f"   Name: {description['name']}")
                    if description["description"]:
                        console.print(f"   Description: {description['description']}")
                    console.print(f"   Stages: {len(description['stages'])}")

                    if description["consistency_issues"]:
                        if isinstance(process, ProcessWithErrors):
                            console.print(
                                f"   [red]Issues: {len(description['consistency_issues'])} validation problems[/red]"
                            )
                        else:
                            console.print(
                                f"   [yellow]Issues: {len(description['consistency_issues'])} consistency problems[/yellow]"
                            )

                    console.print()

                except Exception:
                    prefix = "└─" if i == len(processes) - 1 else "├─"
                    console.print(f"{prefix} ❌ @{process_name}")
                    console.print("   [red]Status: Invalid (severe error)[/red]")
                    console.print()

            console.print(
                "💡 Use 'stageflow view @process_name' to inspect a specific process"
            )

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e


@reg_app.command(name="import")
def import_process(
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
    try:
        if not file_path.exists():
            raise typer.BadParameter(f"File '{file_path}' not found")

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
                console.print_json(data={"error": error_msg, "exists": True})
            else:
                console.print(f"[red]❌ Error:[/red] {error_msg}")
            raise typer.Exit(1)

        # Load process to validate it
        process = load_process(str(file_path))

        # Save to registry
        registry.save_process(registry_name, process)

        action = (
            "overwritten"
            if registry.process_exists(registry_name) and force
            else "imported"
        )

        if json_output:
            result = {
                "message": f"Process {action} successfully",
                "source_file": str(file_path),
                "registry_name": registry_name,
                "overwritten": force,
            }
            console.print_json(data=result)
        else:
            show_success(f"Process {action} to registry as '@{registry_name}'")

    except typer.Exit:
        raise
    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e


@reg_app.command(name="export")
def export_process(
    name: Annotated[str, typer.Argument(help="Registry process name (without @)")],
    file_path: Annotated[Path, typer.Argument(help="Destination file path")],
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Export a registry process to a file."""
    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        # Get source file
        source_path = registry.get_process_file_path(name)
        if not source_path or not source_path.exists():
            raise typer.BadParameter(f"Process '{name}' not found in registry")

        # Copy file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, file_path)

        if json_output:
            result = {
                "message": "Process exported successfully",
                "registry_name": name,
                "destination_file": str(file_path),
            }
            console.print_json(data=result)
        else:
            show_success(f"Process '@{name}' exported to {file_path}")

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e


@reg_app.command(name="delete")
def delete_process(
    name: Annotated[str, typer.Argument(help="Registry process name (without @)")],
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip confirmation")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output in JSON format")
    ] = False,
):
    """Delete a process from the registry."""
    try:
        config = ManagerConfig.from_env()
        registry = ProcessRegistry(config)

        # Check if process exists
        process_file_path = registry.get_process_file_path(name)
        if not process_file_path:
            raise typer.BadParameter(f"Process '{name}' not found in registry")

        # Confirm deletion (unless forced or JSON mode)
        if not json_output and not force:
            confirmed = typer.confirm(
                f"Are you sure you want to delete process '{name}' from the registry?",
                default=False,
            )
            if not confirmed:
                console.print("Deletion cancelled.")
                return

        registry.delete_process(name, create_backup=True)

        if json_output:
            result = {
                "message": f"Process '{name}' deleted successfully",
                "process": name,
                "file": str(process_file_path),
            }
            console.print_json(data=result)
        else:
            show_success(f"Process '{name}' deleted from registry")

    except Exception as e:
        if json_output:
            console.print_json(data={"error": str(e)})
        else:
            console.print(f"[red]❌ Error:[/red] {e}")
        raise typer.Exit(1) from e
