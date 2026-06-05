# Compute Context

## Execution Preference

- Prefer GPU-backed execution over CPU for local inference stages when the selected provider or runtime supports it.
- Keep CPU execution as the required fallback path so Linux and macOS remain usable without a dedicated GPU.
- Make hardware selection explicit in provider configuration or application orchestration rather than hiding it in the CLI surface.

## Current Applicability

- Transcription is the main stage expected to benefit from GPU acceleration through `faster-whisper`.
- Local LLM generation through Ollama should preserve the same preference for GPU-backed execution when the local runtime can use it.
- FFmpeg audio preparation and Pandoc/LaTeX PDF rendering remain CPU-oriented unless a future adapter adds a documented acceleration path with clear operational value.

## Artifact And Logging Rules

- Persist enough metadata to explain whether a stage ran with GPU acceleration or fell back to CPU.
- Never make artifact compatibility depend on the selected compute device.
- Failure messages should distinguish provider or runtime issues from missing GPU capability when that changes remediation.

## Platform Notes

- Linux and macOS stay as the official targets.
- GPU acceleration may differ by runtime and platform, so adapters must degrade gracefully to CPU when acceleration is unavailable.
