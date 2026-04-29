# Technical Context

## Runtime Stack

- Python 3.11+
- Typer for CLI composition
- Rich for output and diagnostics
- Pydantic and pydantic-settings for validated settings
- httpx for future HTTP-based providers
- tomli-w for config file creation

## External Tools

- `ffmpeg` for media extraction and normalization
- `pandoc` plus `xelatex` or `lualatex` for PDF generation
- `ollama` for local LLM inference

These remain external system dependencies rather than bundled Python dependencies.

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
