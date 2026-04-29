# Testing Context

## Unit Coverage Priorities

- Media classification by extension
- Artifact directory naming and overwrite policy
- Prompt template loading from package resources
- Config loading from TOML plus environment variables
- Secret redaction
- Command construction for external adapters
- Error mapping across application and infrastructure boundaries

## Integration Coverage Priorities

- `media-report --help`
- `media-report templates list`
- `media-report config init`
- `media-report doctor`
- `media-report process` bootstrap planning and artifact creation

## Strategy

- Keep core logic free of subprocess calls where possible.
- Mock heavyweight integrations.
- Keep fixtures small and repository-local.
