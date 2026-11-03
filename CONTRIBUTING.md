# Contributing

Thanks for helping. Bug reports, acquirer-specific result codes and documentation fixes are all welcome.

## Set up

```bash
git clone https://github.com/xeroxzen/oppwa-guard.git
cd oppwa-guard
uv sync
```

## Before you open a pull request

All four must pass with no warnings:

```bash
uv run pytest
uv run mypy src tests
uv run ruff check .
uv run ruff format --check .
```

- Add a test that fails without your change.
- Keep functions short enough to read on one screen.
- Public functions document what they raise.
- Update the [reference docs](docs/reference/api.md) and the [changelog](CHANGELOG.md) when behaviour changes.

## Adding a result code

Include a link to the acquirer's public documentation for the code in the pull request, and add the code to the parametrised `test_classify` cases.

## Security issues

Don't open a public issue. See [SECURITY.md](SECURITY.md).
