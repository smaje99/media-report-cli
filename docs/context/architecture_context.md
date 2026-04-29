# Architecture Context

## Style

The project uses hexagonal architecture with moderate vertical slicing.

## Layers

- `media_report.cli`: command definition and console UX
- `media_report.application`: workflow orchestration and use-case services
- `media_report.domain`: entities, value objects, ports, and domain rules
- `media_report.infrastructure`: filesystem, subprocess, HTTP, and package-resource adapters

## Stable Ports

- `TranscriptionProvider`
- `LLMProvider`
- `PromptTemplateRepository`
- `DocumentRenderer`
- `MediaProcessingService`

## Key Decisions

- Resource loading goes through `importlib.resources`.
- Config is user-scoped and file-backed with env overrides.
- Artifact metadata is designed for resumable workflows even before resume support is implemented.
