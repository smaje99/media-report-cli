# Release Notes

## Scope

This project is packaged for PyPI and should always be validated as an installable CLI, not only as a source checkout.

## Release Checklist

1. Run `uv sync --extra dev`.
2. Run `uv run pytest`.
3. Run `uv run ruff check .`.
4. Run `uv run ruff format --check .`.
5. Run `uv run python -m build`.
6. Run `uv run twine check dist/*`.
7. Verify `uv tool install .`.
8. Verify `pipx install .`.
9. Run `media-report doctor`.
10. Smoke test `media-report templates list` and `media-report process tests/fixtures/example.mp3`.

## Platform Policy

- Linux and macOS are the supported release targets.
- Windows is experimental and should not block release unless a regression was explicitly introduced there.

## Packaging Constraints

- Keep runtime resources inside `src/media_report/templates`.
- Load resources through `importlib.resources`.
- Do not add heavyweight external tools to Python runtime dependencies.
- Maintain the public console script name `media-report`.
