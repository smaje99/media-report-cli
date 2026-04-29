# Transcription Provider

## Goal

Add or modify adapters behind the `TranscriptionProvider` port.

## When To Use

- Adding faster-whisper
- Evaluating a new transcription backend
- Changing transcript persistence rules

## Steps

1. Start from the port contract.
2. Map provider output into domain transcript structures.
3. Persist raw text, segments, and provider metadata.
4. Keep provider-specific setup inside infrastructure.
5. Test selection and error mapping with mocks.

## Checklist

- Port contract remains stable
- Metadata includes model and language info when available
- Failures preserve upstream artifacts

## Exit Criteria

The provider is swappable without CLI or domain rewrites.
