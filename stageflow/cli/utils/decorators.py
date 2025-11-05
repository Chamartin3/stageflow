"""Decorators for CLI error handling and consistent output formatting."""

from collections.abc import Callable
from functools import wraps

import typer


def handle_cli_errors(error_message: str) -> Callable:
    """Decorator to handle CLI errors with consistent formatting.

    This decorator catches exceptions and formats them based on json_mode,
    ensuring consistent error handling across all CLI commands.

    Args:
        error_message: Base error message template (can include {error} placeholder)

    Returns:
        Decorated function that handles errors consistently

    Example:
        Instead of manually handling errors like this:

        ```python
        def diagram_command(ctx: typer.Context, ...):
            try:
                generator = MermaidDiagramGenerator()
                diagram = generator.generate_process_diagram(process)
            except Exception as e:
                if json_output:
                    cli_ctx.print_json(data={"error": f"Failed to generate diagram: {e}"})
                else:
                    cli_ctx.print_error(f"Failed to generate diagram: {e}")
                raise typer.Exit(1) from e
        ```

        You can use the decorator:

        ```python
        @handle_cli_errors("Failed to generate diagram")
        def diagram_command(ctx: typer.Context, ...):
            generator = MermaidDiagramGenerator()
            diagram = generator.generate_process_diagram(process)
        ```

        The decorator handles json_mode detection and error formatting automatically.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context from first argument (standard Typer pattern)
            ctx = args[0] if args else kwargs.get("ctx")
            if not ctx or not hasattr(ctx, "obj"):
                # If no context, just run the function normally
                return func(*args, **kwargs)

            cli_ctx = ctx.obj

            try:
                return func(*args, **kwargs)
            except typer.Exit:
                # Re-raise typer.Exit without modification
                raise
            except Exception as e:
                # Format error message
                if "{error}" in error_message:
                    formatted_message = error_message.format(error=e)
                else:
                    formatted_message = f"{error_message}: {e}"

                # Print error based on json_mode
                if hasattr(cli_ctx, "json_mode") and cli_ctx.json_mode:
                    cli_ctx.print_json(data={"error": formatted_message})
                else:
                    cli_ctx.print_error(formatted_message)

                # Exit with error code
                raise typer.Exit(1) from e

        return wrapper

    return decorator
