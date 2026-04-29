# Testing Strategy

## Goal

Write useful tests without binding the suite to heavyweight local dependencies.

## When To Use

- Adding coverage for new logic
- Fixing regressions
- Expanding CLI behavior

## Steps

1. Start with unit coverage for pure logic.
2. Add integration coverage for public CLI behavior.
3. Mock external binaries and remote calls.
4. Use small local fixtures.
5. Keep assertions focused on user-visible behavior and artifacts.

## Checklist

- Unit and integration coverage are balanced
- Tests do not require GPU models by default
- Public CLI changes have integration coverage

## Exit Criteria

The suite catches regressions without becoming fragile or slow.
