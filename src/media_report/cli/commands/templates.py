from __future__ import annotations

import typer
from rich.table import Table

from media_report.core.console import console
from media_report.core.resources import list_pdf_templates, list_prompt_templates

templates_app = typer.Typer(help="Inspect bundled templates.")


@templates_app.command("list")
def templates_list() -> None:
    table = Table(title="Bundled Templates")
    table.add_column("Type")
    table.add_column("Name")

    for name in list_prompt_templates():
        table.add_row("prompt", name)

    for name in list_pdf_templates():
        table.add_row("pdf", name)

    console.print(table)
