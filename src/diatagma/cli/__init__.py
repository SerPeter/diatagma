"""CLI entry point — ``diatagma`` command.

Registers all subcommands from cli/commands/.
"""

from diatagma.cli.app import app

__all__ = ["app"]
