from __future__ import annotations

import typer

from media_report.cli.commands.config import config_app
from media_report.cli.commands.doctor import doctor_command
from media_report.cli.commands.process import process_command
from media_report.cli.commands.templates import templates_app

app = typer.Typer(
    name="media-report",
    help="Process local media into traceable report artifacts.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.command("process")(process_command)
app.command("doctor")(doctor_command)
app.add_typer(config_app, name="config")
app.add_typer(templates_app, name="templates")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
