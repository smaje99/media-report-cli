# LLM Context

## Provider Model

The reporting layer depends on the `LLMProvider` port. Initial adapters are planned for:

- Ollama
- OpenAI-compatible APIs

Future adapters can include Anthropic, Gemini, Groq, OpenRouter, or LM Studio.

## Prompting

- Prompt templates are packaged resources.
- The selected template must be persisted as `prompt_used.md`.
- Raw provider output must be persisted as `llm_response_raw.txt`.

## Privacy

- Local-first providers are preferred by default.
- Remote providers require explicit user choice.
- The CLI must emit a warning when a remote provider is selected.

## Compute Preference

- Local providers should prefer GPU-backed execution when their runtime can use the machine's graphics hardware.
- CPU fallback must remain available so report generation does not require a GPU-only environment.
- Device selection and fallback behavior should be observable in metadata or logs without exposing secrets.

## Failure Rules

- If report generation fails, preserve transcription artifacts and metadata.
- Report generation errors should include provider and model context without exposing secrets.
