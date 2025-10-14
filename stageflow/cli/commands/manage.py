"""
Manage CLI command for StageFlow process management operations.

Provides a clean interface for all process management operations while
delegating the actual work to the utility functions.
"""

import click

from stageflow.manager import ProcessManager
from stageflow.manager.utils import (
    list_all_processes,
    sync_all_processes,
    add_stage_to_process,
    remove_stage_from_process,
    sync_process,
    create_new_process,
    create_process_with_default_schema,
    create_process_with_default,
    edit_process_file,
    validate_process_operations,
)


@click.command()
@click.option(
    "--list", "list_processes",
    is_flag=True,
    help="List all available processes"
)
@click.option(
    "--process", "process_name",
    type=str,
    help="Process name to operate on"
)
@click.option(
    "--add-stage", "add_stage_config",
    type=str,
    help="Add stage to process (JSON configuration)"
)
@click.option(
    "--remove-stage", "remove_stage_name",
    type=str,
    help="Remove stage from process by name"
)
@click.option(
    "--sync", "sync_process_flag",
    is_flag=True,
    help="Save process changes to file"
)
@click.option(
    "--sync-all", "sync_all_processes_flag",
    is_flag=True,
    help="Save all modified processes to files"
)
@click.option(
    "--create", "create_process_flag",
    is_flag=True,
    help="Create new process using default schema"
)
@click.option(
    "--create-json", "create_process_definition",
    type=str,
    help="Create new process from JSON definition"
)
@click.option(
    "--create-default", "create_default_process",
    is_flag=True,
    help="Create new process using default schema"
)
@click.option(
    "--default-schema", "default_schema_template",
    type=click.Choice(['basic', 'approval', 'onboarding'], case_sensitive=False),
    help="Create process using default schema template (basic, approval, onboarding)"
)
@click.option(
    "--edit", "edit_process",
    is_flag=True,
    help="Open process file in text editor"
)
def manage(list_processes, process_name, add_stage_config, remove_stage_name,
          sync_process_flag, sync_all_processes_flag, create_process_flag, create_process_definition,
          create_default_process, default_schema_template, edit_process):
    """
    Process management operations.

    This command provides a comprehensive interface for managing StageFlow processes
    including listing, editing, and synchronizing processes.

    Examples:

        # List all processes
        stageflow manage --list

        # Create a new process with default schema
        stageflow manage --process my_workflow --create

        # Create a new process with custom JSON definition
        stageflow manage --process new_workflow --create '{"stages": {"start": {"name": "Start", "gates": []}}, "initial_stage": "start", "final_stage": "start"}'

        # Create a new process using default schema templates
        stageflow manage --process simple_flow --default-schema basic
        stageflow manage --process content_review --default-schema approval
        stageflow manage --process user_signup --default-schema onboarding

        # Create a new process using the basic default schema
        stageflow manage --process my_workflow --create-default

        # Edit an existing process file in text editor
        stageflow manage --process my_workflow --edit

        # Add a stage to a process
        stageflow manage --process user_flow --add-stage '{"name": "verification", "gates": []}'

        # Remove a stage from a process
        stageflow manage --process user_flow --remove-stage verification

        # Save a specific process
        stageflow manage --process user_flow --sync

        # Save all modified processes
        stageflow manage --sync-all
    """
    try:
        manager = ProcessManager()
    except Exception as e:
        click.echo(f"Error: Failed to initialize process manager: {e}", err=True)
        raise click.Abort()

    # Handle global operations first (don't require --process)
    if list_processes:
        result = list_all_processes(manager)
        if result.success and result.data:
            if result.data:
                click.echo("Available processes:")
                for name in sorted(result.data):
                    click.echo(f"  {name}")
            else:
                click.echo("No processes found")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()
        return

    if sync_all_processes_flag:
        result = sync_all_processes(manager)
        if result.success:
            if result.data:
                click.echo("Sync results:")
                for name, success in result.data.items():
                    status = "✓" if success else "✗"
                    click.echo(f"  {status} {name}")
            else:
                click.echo("No processes had pending changes")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()
        return

    # Validate process-specific operations
    validation = validate_process_operations(
        process_name, add_stage_config, remove_stage_name, sync_process_flag,
        create_process_definition, default_schema_template is not None,
        create_default_process, edit_process, create_process_flag
    )
    if not validation.success:
        click.echo(f"Error: {validation.message}", err=True)
        raise click.Abort()

    # Handle create operations first
    if create_process_flag:
        # Create with default schema when --create flag is used
        result = create_process_with_default(manager, process_name)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if create_process_definition:
        # Create with provided JSON definition
        result = create_new_process(manager, process_name, create_process_definition)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if default_schema_template:
        result = create_process_with_default_schema(manager, process_name, default_schema_template)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if create_default_process:
        result = create_process_with_default(manager, process_name)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if edit_process:
        result = edit_process_file(manager, process_name)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    # Default action when no flags provided - list processes
    if not any([add_stage_config, remove_stage_name, sync_process_flag, create_process_definition,
                default_schema_template, create_default_process, edit_process, create_process_flag]):
        result = list_all_processes(manager)
        if result.success and result.data:
            if result.data:
                click.echo("Available processes:")
                for name in sorted(result.data):
                    click.echo(f"  {name}")
            else:
                click.echo("No processes found")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()
        return

    # Execute process-specific operations
    if add_stage_config:
        result = add_stage_to_process(manager, process_name, add_stage_config)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if remove_stage_name:
        result = remove_stage_from_process(manager, process_name, remove_stage_name)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()

    if sync_process_flag:
        result = sync_process(manager, process_name)
        if result.success:
            click.echo(f"✓ {result.message}")
        else:
            click.echo(f"Error: {result.message}", err=True)
            raise click.Abort()