# CLI Design

## Goal

Design stable, explicit Typer commands and Rich-driven output for `media-report`.

## When To Use

- Adding a command
- Changing flags or defaults
- Improving help text or error messages

## Steps

1. Start from the user task and resulting artifacts.
2. Keep command names and options explicit.
3. Decide which output is for humans and which is persisted as artifacts.
4. Validate failure messages for actionable guidance.
5. Add integration coverage for public behavior.

## Checklist

- Help output is readable
- Defaults are documented
- Errors map to non-zero exits
- New flags are additive unless documented otherwise

## Exit Criteria

The command is discoverable, stable, and covered by integration tests.
