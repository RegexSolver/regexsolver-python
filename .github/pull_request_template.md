## What this changes

<!-- And why. Link the issue it closes, if there is one. -->

## Checklist

- [ ] `flake8 regexsolver tests`, `mypy regexsolver` and `pytest` pass
- [ ] New public items carry a docstring, and anything user-facing is in the README
- [ ] A test covers the change
- [ ] `CHANGELOG.md` is updated under `## [Unreleased]`
- [ ] The change runs on Python 3.10, the version `requires-python` declares, or the bump is intentional and noted
- [ ] `regexsolver/_generated/` is only touched by `./generate-api.sh`, once the change is live in the API's published specification
