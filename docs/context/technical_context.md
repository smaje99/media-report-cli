# Technical Context

## Runtime Stack

- Python 3.11+
- Typer for CLI composition
- Rich for output and diagnostics
- Pydantic and pydantic-settings for validated settings
- httpx for future HTTP-based providers
- tomli-w for config file creation

Typed integration boundaries for third-party SDKs should stay private to their
infrastructure adapters when they only describe the minimum external shape needed by that adapter.

## External Tools

- `ffmpeg` for media extraction and normalization
- `pandoc` plus `xelatex` or `lualatex` for PDF generation
- `ollama` for local LLM inference

These remain external system dependencies rather than bundled Python dependencies.

## Compute Strategy

- Prefer GPU-backed execution for local inference workloads when the provider supports it.
- Keep CPU fallback mandatory for transcription and local LLM flows so the CLI still works on machines without usable GPU acceleration.
- Treat compute-device selection as an infrastructure and application concern, not a CLI-only shortcut.
- See [compute_context.md](./compute_context.md) for the cross-stage policy.

## Packaging

- `src/` layout
- Hatchling build backend
- Package resources loaded with `importlib.resources`
- End-user installation path is `uv tool install` or `pipx install`

## Platform Constraints

- Linux and macOS supported
- Windows experimental
- No GUI assumptions
- No fragile repository-relative resource loading
