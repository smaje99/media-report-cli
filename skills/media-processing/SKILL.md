# Media Processing

## Goal

Implement and evolve FFmpeg-based extraction and normalization safely.

## When To Use

- Working on source media inspection
- Building FFmpeg command execution
- Handling audio extraction or normalization failures

## Steps

1. Validate source media type.
2. Build commands deterministically.
3. Keep subprocess calls in infrastructure.
4. Capture stderr for readable error mapping.
5. Persist stage status and produced artifact paths.

## Checklist

- Commands are explicit
- Output filenames are stable
- Errors remain understandable
- Tests cover command construction

## Exit Criteria

Media processing changes are reproducible and failure-safe.
