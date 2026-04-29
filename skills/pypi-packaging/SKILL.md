# PyPI Packaging

## Goal

Keep the project aligned with PyPI distribution requirements from the start.

## When To Use

- Editing `pyproject.toml`
- Adding package data
- Changing entry points or metadata

## Steps

1. Confirm the package name, import package, and console script names.
2. Use `src/` layout.
3. Keep metadata, classifiers, and URLs complete.
4. Ensure non-code resources are included in build outputs.
5. Verify installation through isolated tool flows.

## Checklist

- `media-report-cli` package metadata is complete
- `media_report` imports cleanly
- `media-report` entry point resolves
- Resources ship in wheel and sdist

## Exit Criteria

The project is ready for PyPI publication and isolated installation.
