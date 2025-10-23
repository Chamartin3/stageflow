"""CLI commands module for StageFlow."""

from stageflow.cli.commands.diagram import diagram_command
from stageflow.cli.commands.evaluate import evaluate_command
from stageflow.cli.commands.new import new_command
from stageflow.cli.commands.registry import reg_app
from stageflow.cli.commands.view import view_command

__all__ = [
    "view_command",
    "evaluate_command",
    "new_command",
    "diagram_command",
    "reg_app",
]
