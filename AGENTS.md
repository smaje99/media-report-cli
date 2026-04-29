# AGENTS

## Purpose

`media-report-cli` is a distributable Python CLI that converts local media into traceable reporting artifacts. The package name is `media-report-cli`, the import package is `media_report`, and the global command is `media-report`.

## Required Architecture

- Use hexagonal architecture with moderate vertical slicing.
- Keep CLI concerns in `media_report.cli`.
- Keep orchestration in `media_report.application`.
- Keep business rules, entities, and ports in `media_report.domain`.
- Keep adapters and subprocess or HTTP integrations in `media_report.infrastructure`.
- Load packaged resources through `importlib.resources`.

## Release And Distribution Rules

- Treat PyPI distribution as a first-class concern from the first commit.
- Preserve `src/` layout.
- Do not depend on repository-relative paths at runtime.
- Keep Linux and macOS as the official targets.
- Treat Windows as experimental and document regressions clearly.

## CLI Compatibility Rules

- Do not rename the root command `media-report`.
- Keep bootstrap commands available:
  - `process`
  - `doctor`
  - `config init`
  - `config show`
  - `templates list`
- New options should be additive unless a deprecation path is documented.

## Security Rules

- Never print API keys or tokens.
- Redact secrets in config output, metadata, and logs.
- Default to local execution paths where possible.
- Emit a clear warning when the user chooses a remote LLM provider.

## Testing Rules

- Add or update unit tests for domain and adapter behavior.
- Add integration tests for CLI entry points when public command behavior changes.
- Keep heavy external dependencies mocked in tests unless a test is explicitly marked as an environment integration.

## Development Commands

- `uv sync --extra dev`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`
- `uv run python -m build`
- `uv run twine check dist/*`

## Commit Conventions

- Use focused commits with conventional prefixes such as `feat:`, `fix:`, `docs:`, `test:`, or `chore:`.
- Keep packaging, docs, and code changes separated when practical.

## Extensibility Rules

### Adding An LLM Provider

- Implement the `LLMProvider` port.
- Keep HTTP client behavior inside infrastructure adapters.
- Make provider selection explicit in configuration and application orchestration.
- Persist raw prompt and response artifacts for traceability.

### Adding A Transcription Provider

- Implement the `TranscriptionProvider` port.
- Keep model loading and inference logic outside the CLI layer.
- Persist raw text, segment data, and provider metadata.

### Adding A Report Template

- Add the Markdown prompt template under `src/media_report/templates/prompts`.
- Make it discoverable via `templates list`.
- Document intended use and expected report structure.

## Definition Of Done

- Code follows the architecture boundaries above.
- Tests cover the new behavior.
- Public CLI help text remains coherent.
- Packaged resources still work from installed contexts.
- Secrets remain redacted.
- Relevant docs are updated when the user-facing workflow changes.
