---
name: llm-provider
description: Implement or refine report generation providers behind the LLMProvider port. Use when adding OpenAI-compatible providers, Ollama support, provider configuration, or prompt and artifact persistence behavior.
---

# LLM Provider

## Goal

Implement or refine report-generation providers behind the `LLMProvider` port.

## When To Use

- Adding OpenAI-compatible support
- Adding Ollama or another model host
- Updating provider configuration behavior

## Steps

1. Keep prompt rendering separate from transport.
2. Model request and response payloads explicitly.
3. Redact secrets everywhere.
4. Emit remote-provider privacy warnings from CLI or application policy.
5. Persist prompt and raw response artifacts.

## Checklist

- Provider is selected through config or CLI options
- HTTP concerns stay in infrastructure
- Error messages include provider and model context

## Exit Criteria

Providers are interchangeable and traceable.
