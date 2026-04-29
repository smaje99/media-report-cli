# PDF Generation

## Goal

Convert report Markdown to PDF through Pandoc and LaTeX without losing source artifacts.

## When To Use

- Adding Pandoc rendering
- Troubleshooting missing LaTeX engines
- Improving PDF template behavior

## Steps

1. Build Pandoc commands deterministically.
2. Prefer `xelatex`, accept `lualatex`.
3. Keep subprocess execution in infrastructure.
4. Treat Markdown preservation as mandatory.
5. Return actionable dependency errors.

## Checklist

- Markdown survives PDF failures
- Engine selection is explicit
- Tests cover command construction and failure mapping

## Exit Criteria

PDF generation is optional, diagnosable, and non-destructive.
