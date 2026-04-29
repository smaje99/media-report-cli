# Release Packaging

## Goal

Prepare the repository for repeatable builds and installation validation.

## When To Use

- Building a release
- Fixing wheel or sdist issues
- Validating CLI installation paths

## Steps

1. Verify package metadata is complete.
2. Build wheel and sdist.
3. Validate bundled resources from an installed context.
4. Smoke test the console entry point.
5. Record release steps in docs.

## Checklist

- `python -m build` passes
- `twine check` passes
- `uv tool install .` works
- `pipx install .` works

## Exit Criteria

The package installs and runs outside the repository checkout.
