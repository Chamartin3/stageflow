"""
CLI Context for StageFlow.

Provides centralized process loading and context management for all CLI commands.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import Any

import typer
from rich.console import Console

from stageflow.cli.utils.printer import CliPrinter
from stageflow.elements import create_element
from stageflow.loader import LoadError, ProcessLoader, load_element
from stageflow.models import ProcessLoadResult
from stageflow.process import Process


@dataclass
class CLIContext:
    """
    Context object for CLI commands.

    This context is created once and passed to all commands via Typer's
    context injection. It centralizes:
    - Process loading with the improved loader
    - Element loading from files or stdin
    - Error handling and reporting
    - Console output management
    - Verbose mode control
    - JSON mode control (suppresses all non-JSON output)

    Attributes:
        console: Rich console for output
        verbose: Enable verbose output (ignored when json_mode is True)
        printer: CLI printer for formatted output (always initialized)
        loader: Process loader instance (shared across commands)
        process: Loaded process (if loading succeeded)
        load_result: Full load result with errors/warnings
        source: Source identifier (file path or registry name)
        json_mode: When True, suppress all non-JSON output (set by commands)
    """

    console: Console
    verbose: bool = False
    printer: CliPrinter = field(init=False)  # Will be initialized in __post_init__
    loader: ProcessLoader = field(init=False)  # Will be initialized in __post_init__
    process: Process | None = None
    load_result: ProcessLoadResult | None = None
    source: str = ""
    json_mode: bool = False

    def __post_init__(self):
        """Initialize printer and loader."""
        self.printer = CliPrinter(console=self.console, verbose=self.verbose)
        self.loader = ProcessLoader()

    def _should_print_verbose(self) -> bool:
        """Check if verbose output should be printed (not in JSON mode)."""
        return self.verbose and not self.json_mode

    def print_verbose(self, message: str, **kwargs) -> None:
        """
        Print a message only if verbose mode is enabled and not in JSON mode.

        Args:
            message: Message to print
            **kwargs: Additional arguments passed to console.print()
        """
        if self._should_print_verbose():
            self.console.print(message, **kwargs)

    def print_progress(self, message: str) -> None:
        """
        Print a progress message (only in verbose mode, not in JSON mode).

        Args:
            message: Progress message to print
        """
        if self._should_print_verbose():
            self.printer.show_progress(message)

    def print_error(self, message: str) -> None:
        """
        Print an error message (always prints unless in JSON mode).

        Args:
            message: Error message to print
        """
        if not self.json_mode:
            self.printer.print_error(message)

    def print_success(self, message: str) -> None:
        """
        Print a success message (always prints unless in JSON mode).

        Args:
            message: Success message to print
        """
        if not self.json_mode:
            self.printer.show_success(message)

    def print_json(self, data: Any) -> None:
        """
        Print data as JSON (always prints, even in JSON mode).

        Args:
            data: Data to serialize and print as JSON
        """
        self.printer.print_json(data=data)

    def load_process_or_exit(self, source: str) -> Process:
        """
        Load process using the improved loader and exit on failure.

        This is the primary method for commands that require a process.
        It handles all error reporting and exits the CLI with code 1 if loading fails.

        Args:
            source: File path or registry identifier

        Returns:
            Process instance (only if successful; otherwise exits)

        Raises:
            typer.Exit: If loading fails
        """
        self.source = source

        self.print_verbose(f"[dim]Loading process from: {source}[/dim]")

        # Use shared loader instance
        result = self.loader.load(source)

        # Store result
        self.load_result = result

        # Check if successful
        if result.success and result.process is not None:
            self.process = result.process

            # Show warnings if any (but continue)
            if result.has_warnings:
                self.printer.print_load_result(result, json_mode=self.json_mode)
            elif self.verbose:
                self.print_verbose("[green]✓ Process loaded successfully[/green]")

            return result.process  # Return the non-None process from result
        else:
            # Loading failed - show errors and exit
            self.printer.print_load_result(result, json_mode=self.json_mode)
            raise typer.Exit(code=1)

    def load_process(self, source: str) -> bool:
        """
        Load process using the improved loader (non-exiting version).

        Use this when you want to handle errors yourself rather than exiting.
        For most commands, use load_process_or_exit() instead.

        Args:
            source: File path or registry identifier

        Returns:
            True if loading succeeded, False otherwise
        """
        self.source = source

        self.print_verbose(f"[dim]Loading process from: {source}[/dim]")

        # Use shared loader instance
        result = self.loader.load(source)

        # Store result
        self.load_result = result

        # Check if successful
        if result.success:
            self.process = result.process
            if self.verbose:
                if result.has_warnings:
                    self.print_verbose(
                        f"[yellow]⚠ Process loaded with {result.warning_count} warning(s)[/yellow]"
                    )
                else:
                    self.print_verbose("[green]✓ Process loaded successfully[/green]")
            return True
        else:
            # Loading failed
            self._show_load_errors()
            return False

    def load_element_or_exit(self, element_path: str | None = None) -> Any:
        """
        Load element from file or stdin and exit on failure.

        This method handles element loading with proper error reporting.
        If element_path is None, reads from stdin.

        Args:
            element_path: Path to element file (JSON/YAML) or None for stdin

        Returns:
            Element instance (only if successful; otherwise exits)

        Raises:
            typer.Exit: If loading fails
        """
        try:
            if element_path:
                # Load from file
                self.print_verbose(f"[dim]Loading element from {element_path}[/dim]")

                try:
                    elem = load_element(str(element_path))
                    self.print_verbose("[green]✓ Element loaded successfully[/green]")
                    return elem
                except LoadError as e:
                    self.printer.print_error(f"Failed to load element: {e}")
                    raise typer.Exit(code=1) from e
            else:
                # Load from stdin
                self.print_verbose("[dim]Reading element from stdin...[/dim]")

                try:
                    stdin_data = sys.stdin.read()
                    if not stdin_data.strip():
                        error_msg = "No data provided on stdin"
                        self.printer.print_error(error_msg)
                        raise typer.Exit(code=1)

                    element_data = json.loads(stdin_data)
                    elem = create_element(element_data)

                    self.print_verbose("[green]✓ Element loaded from stdin[/green]")
                    return elem

                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON from stdin: {e}"
                    self.printer.print_error(error_msg)
                    raise typer.Exit(code=1) from e
                except Exception as e:
                    error_msg = f"Failed to create element from stdin: {e}"
                    self.printer.print_error(error_msg)
                    raise typer.Exit(code=1) from e

        except typer.Exit:
            raise
        except Exception as e:
            error_msg = f"Unexpected error loading element: {e}"
            self.printer.print_error(error_msg)
            raise typer.Exit(code=1) from e

    def _show_load_errors(self) -> None:
        """Display load errors in a user-friendly format."""
        if not self.load_result:
            return

        result = self.load_result

        self.console.print(f"[red]✗ Failed to load process from: {result.source}[/red]")
        self.console.print(f"[red]  Status: {result.status.value}[/red]")
        self.console.print(f"[red]  Errors: {result.error_count}[/red]")

        # Show detailed errors
        if result.has_errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for i, error in enumerate(result.errors, 1):
                self.console.print(f"  {i}. [{error.severity.value}] {error.message}")
                if error.context and self.verbose:
                    for key, value in error.context.items():
                        self.console.print(f"     {key}: {value}")

    def require_process(self) -> Process:
        """
        Get the loaded process or raise an error.

        Returns:
            Process instance

        Raises:
            RuntimeError: If no process has been loaded
        """
        if self.process is None:
            raise RuntimeError(
                "No process loaded. Ensure load_process() is called before commands that require a process."
            )
        return self.process

    def show_warnings(self) -> None:
        """Display any warnings from process loading."""
        if not self.load_result or not self.load_result.has_warnings:
            return

        self.console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for i, warning in enumerate(self.load_result.warnings, 1):
            self.console.print(f"  {i}. [{warning.severity.value}] {warning.message}")
            if warning.context and self.verbose:
                for key, value in warning.context.items():
                    self.console.print(f"     {key}: {value}")

    def print(self, message: str, **kwargs) -> None:
        """Print message to console."""
        self.console.print(message, **kwargs)


def create_cli_context(verbose: bool = False) -> CLIContext:
    """
    Create a new CLI context.

    Args:
        verbose: Enable verbose output

    Returns:
        CLIContext instance
    """
    console = Console()
    return CLIContext(console=console, verbose=verbose)
