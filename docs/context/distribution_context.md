# Distribution Context

## Distribution Target

The primary distribution channel is PyPI.

## Installation Modes

- `uv tool install media-report-cli`
- `pipx install media-report-cli`
- `pip install media-report-cli`

The first two are the recommended end-user options because they isolate dependencies.

## Packaging Requirements

- Console script: `media-report`
- Import package: `media_report`
- Resources bundled under `src/media_report/templates`
- Wheel and sdist must include prompt and PDF templates

## Validation

Every release should verify:

- `uv tool install .`
- `pipx install .`
- `uv run python -m build`
- `uv run twine check dist/*`
