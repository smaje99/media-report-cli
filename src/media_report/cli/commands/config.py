from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.pretty import Pretty

from media_report.core.console import console
from media_report.core.settings import (
  default_config_data,
  load_settings,
  redact_settings,
  write_default_config,
)

config_app = typer.Typer(help="Manage configuration.")


@config_app.command("init")
def config_init(
  force: Annotated[
    bool,
    typer.Option("--force", help="Overwrite an existing config file."),
  ] = False,
  path: Annotated[
    Path | None,
    typer.Option("--path", help="Optional target config file path."),
  ] = None,
) -> None:
  """Write a default config skeleton to the standard path or a custom target."""
  try:
    target = write_default_config(path=path, force=force)
  except FileExistsError as exc:
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=2) from exc
  console.print(f"Config written to {target}")


@config_app.command("show")
def config_show() -> None:
  """Print the effective configuration with secrets redacted."""
  settings = load_settings()
  console.print(Pretty(redact_settings(settings)))
  if not settings.config_path.exists():
    console.print(
      "[yellow]Note:[/yellow] no config file exists yet; showing defaults and env overrides."
    )


@config_app.command("example", hidden=True)
def config_example() -> None:
  """Print the default config data without writing to a file."""
  console.print(Pretty(default_config_data()))
