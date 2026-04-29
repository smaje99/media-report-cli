# media-report-cli

`media-report-cli` is a Python package and console application for turning local audio or video files into structured reporting artifacts.

The distribution target is PyPI. The import package is `media_report`, and the global command is `media-report`.

## Status

Version `0.1.0` is a bootstrap release focused on packaging, configuration, CLI ergonomics, artifact planning, and developer scaffolding.

- Official platforms: Linux and macOS
- Windows: experimental, best-effort only

## Installation

End-user installation should prefer isolated tool environments:

```bash
uv tool install media-report-cli
```

or

```bash
pipx install media-report-cli
```

Repository-local development:

```bash
uv sync --extra dev
uv run media-report doctor
```

Repository-local tool install:

```bash
uv tool install .
```

## CLI Surface

```bash
media-report process PATH [OPTIONS]
media-report doctor
media-report config init
media-report config show
media-report templates list
```

Example usage:

```bash
media-report process ./meeting.mp4
media-report process ./recordings --recursive --template meeting
media-report process ./lecture.mp3 --provider openai-compatible --model gpt-4.1-mini --language es
media-report doctor
media-report config init
```

## What 0.1.0 Does

- Validates media input paths
- Detects supported audio and video files
- Creates per-file artifact directories next to the source media
- Writes bootstrap `metadata.json` and `pipeline.log`
- Loads packaged prompt and PDF templates from installed package resources
- Checks external tooling availability with `doctor`
- Manages config at `~/.config/media-report/config.toml`

Full FFmpeg, transcription, LLM generation, and PDF rendering adapters are scaffolded as interfaces for later phases but are not yet wired into a full end-to-end processing pipeline.

## External Dependencies

The package intentionally keeps heavyweight tools external to the Python dependency graph:

- `ffmpeg`
- `pandoc`
- `xelatex` or `lualatex`
- `ollama`

Optional Python dependencies:

- `faster-whisper` via the `transcription` extra

## Configuration

Config file path:

```text
~/.config/media-report/config.toml
```

Supported environment variables:

- `MEDIA_REPORT_LLM_PROVIDER`
- `MEDIA_REPORT_LLM_MODEL`
- `MEDIA_REPORT_OPENAI_API_KEY`
- `MEDIA_REPORT_OPENAI_BASE_URL`
- `MEDIA_REPORT_OLLAMA_BASE_URL`
- `MEDIA_REPORT_WHISPER_MODEL`
- `MEDIA_REPORT_OUTPUT_FORMAT`
- `MEDIA_REPORT_LOG_LEVEL`

Environment variables override file values. `media-report config show` always redacts secrets.

## Privacy

The default local path is designed around local tools such as Ollama and, later, faster-whisper.

- Secrets are redacted in CLI output.
- Remote processing is opt-in by provider choice.
- The CLI warns when a remote LLM provider is selected.
- Intermediate artifacts are preserved for traceability unless future workflow stages explicitly change that policy.

## Packaging Notes

Bundled prompt templates and the default LaTeX template are loaded with `importlib.resources` so they work from:

- `uv tool install media-report-cli`
- `pipx install media-report-cli`
- `pip install media-report-cli`

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run ruff format .
uv run python -m build
uv run twine check dist/*
```

See [docs/release.md](docs/release.md) and [AGENTS.md](AGENTS.md) for project-specific rules.
