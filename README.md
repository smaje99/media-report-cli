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

## Bootstrap Contract

Version `0.1.0` treats the current bootstrap CLI surface as stable:

- Root command: `media-report`
- Stable bootstrap commands: `process`, `doctor`, `config init`, `config show`, `templates list`
- Additive evolution only for new public options and commands

`media-report process` keeps all currently visible flags public, with these current semantics:

| Flag group | Flags | Bootstrap status |
| --- | --- | --- |
| Active now | `--recursive`, `--resume`, `--template` | Affect discovery, artifact reuse, and template planning today |
| Deprecated compatibility | `--overwrite` | Deprecated alias for `--resume` during Sprint 2; destructive overwrite is intentionally not exposed yet |
| Active for planning | `--provider`, `--model`, `--output-format` | Affect planned workflow metadata and remote-provider warning today |
| Planning selectors | `--only-transcribe`, `--only-report` | Constrain the planned stage set today; `--only-report` requires reusable transcription artifacts and `--resume` |
| Metadata planning | `--language` | Recorded in pipeline metadata for future transcription execution |

Example usage:

```bash
media-report process ./meeting.mp4
media-report process ./meeting.mp4 --resume
media-report process ./recordings --recursive --template meeting
media-report process ./lecture.mp3 --provider openai-compatible --model gpt-4.1-mini --language es
media-report process ./lecture.mp3 --resume --only-report
media-report doctor
media-report config init
```

## What 0.1.0 Does

- Validates media input paths
- Detects supported audio and video files
- Creates per-file artifact directories next to the source media
- Writes bootstrap `metadata.json` and `pipeline.log`
- Reuses valid sibling artifact directories when invoked with `--resume`
- Validates existing metadata strictly before planning a resumed run
- Prints per-stage planning decisions (`planned`, `reused`, `skipped`)
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
