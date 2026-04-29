# Hexagonal Architecture

## Goal

Keep domain rules isolated from CLI, filesystem, subprocess, and HTTP details.

## When To Use

- Adding new orchestration logic
- Introducing external integrations
- Refactoring workflow code

## Steps

1. Identify the port the use case needs.
2. Model the domain entities and errors first.
3. Keep orchestration in the application layer.
4. Implement adapters in infrastructure only.
5. Verify imports flow inward, not outward.

## Checklist

- Domain does not import Typer, Rich, subprocess, or httpx adapters
- Application depends on ports, not concrete integrations
- Infrastructure implements the ports

## Exit Criteria

The feature can be tested without invoking real external systems.
