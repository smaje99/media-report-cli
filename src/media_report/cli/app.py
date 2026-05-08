from __future__ import annotations

import typer

from media_report.cli.commands.config import config_app
from media_report.cli.commands.doctor import doctor_command
from media_report.cli.commands.process import process_command
from media_report.cli.commands.templates import templates_app

app = typer.Typer(
    name="media-report",
    help="Process local media into traceable report artifacts.",
    rich_markup_mode="markdown",
)

app.command(
    "process",
    help="Prepare bootstrap artifacts and a stage plan for local media.",
)(process_command)
app.command(
    "doctor",
    help="Inspect the local bootstrap environment and packaged resources.",
)(doctor_command)
app.add_typer(config_app, name="config")
app.add_typer(templates_app, name="templates")


@app.callback(invoke_without_command=True)
def root_callback(ctx: typer.Context) -> None:
    """Show help if no subcommand is invoked."""
    if ctx.invoked_subcommand is None and not ctx.resilient_parsing:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
