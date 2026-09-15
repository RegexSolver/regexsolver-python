# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-08

The singleton `RegexSolver` becomes an instantiable `RegexSolverClient`, with `AsyncRegexSolverClient` beside it, every operation moves from `Term` onto the client, and the SDK covers the whole API rather than the seven endpoints it knew about. The API moved with it, to a new contract served under `/v1`, so 1.0.x no longer reaches an endpoint that exists; see *Compatibility* below.

### Added

- `RegexSolverClient(api_token, base_url=..., auto_batch=True, max_terms_per_request=None)` and `AsyncRegexSolverClient`, taking the same arguments. Several clients, each with its own token, can exist in one process; both work as context managers and release their session on `close()` / `aclose()`. The synchronous client drives the asynchronous one on a shared background event loop.
- The operations the API gained since 1.0.3: `complement`, `concat`, `determinize`, `repeat`, `get_cardinality`, `get_dot`, `get_length`, `is_empty`, `is_empty_string`, `is_total`, `is_deterministic` and `get_account_limits`.
- Keyword options: `response_format` (`REGEX`, `FAIR` or `ANY`), `deterministic` and `execution_timeout` on the operations that return a term; `execution_timeout` alone on analyze operations and `determinize`.
- `generate_strings(term, limit, offset, ...)`, which pages through the language instead of returning a fixed count from the start, taking `path_order`, `character_order`, `seed`, `min_length`, `max_length` and `charset`. Paging is only consistent over a deterministic FAIR, hence `determinize()` and `is_deterministic()`.
- `Term.matches(string)`, evaluated locally with `re` — anchored `\A(?:...)\Z`, compiled with `re.DOTALL` — rather than by the API. It raises on a FAIR whose pattern is not known yet, and returns `False` for the empty language, which the engine writes as `[]`.
- An exception hierarchy under `RegexSolverError`, so a caller can catch the case it handles instead of matching on a message. `ApiError` carries `status_code` and `body`, and splits per status down to `RegexSyntaxError`, `TimeoutExceededError`, `QuotaExceededError` and the rest.
- A rate limiter, shared by every client holding the same token: a 429 sets a deadline from `Retry-After`, requests wait for it, and the operation is retried within a five-minute budget.
- Automatic batching: `concat`, `intersection` and `union` split a call carrying more terms than the account allows per request and fold the results back into one, each constituent request counting against the monthly quota. Disable with `auto_batch=False`, or lower the split with `max_terms_per_request`.
- A per-term cache of what the API has already returned — cardinality, length, pattern, dot, and the empty, empty-string, total and deterministic flags — so asking twice costs one request.
- `Term.serialize()` / `Term.deserialize()`, round-tripping the `regex=<pattern>` / `fair=<payload>` form, plus `__eq__`, `__hash__`, `get_value()`, `to_dto()` and `from_dto()`.
- `AccountLimits`, `Cardinality` (`Integer`, `BigInteger`, `Infinite`), `Length`, `ResponseFormat`, `PathOrder` and `CharacterOrder` as exported models.
- `generate-api.sh`, which regenerates `regexsolver/_generated/` from the specification the API publishes at `https://api.regexsolver.com/openapi.json`; `.openapi-generator-ignore` protects the hand-written files.
- CI running flake8 and mypy, then the tests on Python 3.10 through 3.14, on pushes to `main`, on pull requests, and before a release is published.
- A `CHANGELOG.md`, this file, a pull request template, and Dependabot updates.

### Changed

- The HTTP layer is an `asyncio` client generated from the OpenAPI specification, on `aiohttp`, instead of hand-written `requests` calls, with `regexsolver/` the hand-written surface over `regexsolver/_generated/`.
- `Term` is an abstract base class with `RegexTerm` and `FairTerm` subclasses rather than a pydantic model; `Term.regex()` and `Term.fair()` are unchanged.
- `Term.get_pattern()` and `Term.get_fair()` read the term's own value and its cache, returning `None` when the other format has not been resolved yet. Resolving a pattern is `client.get_pattern(term)`.
- The minimum supported Python version is 3.10, declared in `requires-python`, up from 3.7.
- The package is built from `pyproject.toml` alone, with the test dependencies under the `test` extra.
- The tests drive the clients with `unittest.mock` over the generated API instead of matching URLs with `requests_mock` and loading fixtures from `tests/assets/`.

### Removed

- `RegexSolver`, with `get_instance()` and `initialize()`.
- The operation methods on `Term`: `intersection()`, `union()`, `subtraction()`, `is_equivalent_to()`, `is_subset_of()`, `generate_strings()` and `get_details()`.
- `Details`, along with the `regexsolver.details` module, which returned cardinality, length and the empty and total flags in one response.
- `setup.py`, `requirements.txt` and `test-requirements.txt`.

### Compatibility

- `RegexSolver.get_instance().initialize(token)` becomes `RegexSolverClient(token)`, and a term method becomes a client method taking the terms as arguments: `term1.union(term2)` is `client.union(term1, term2)`, `is_equivalent_to` is `equivalent`, `is_subset_of` is `subset`, `subtraction` is `difference`, and `get_details` is `get_cardinality()`, `get_length()`, `is_empty()` and `is_total()`.
- `ApiError` no longer prefixes its message with `The API returned the following error: `; the message text differs and `status_code` is what to branch on.
- The endpoints moved from `https://api.regexsolver.com/api/*` to `/v1/*`, and `/api/analyze/details` is split into one `/v1/analyze/*` endpoint per property. 1.1.0 is the lowest version that works against the API.
- The serialized `regex=` / `fair=` form is unchanged, so a term persisted by 1.0.x deserializes.

## [1.0.3] - 2024-08-11

### Fixed

- `Length.minimum` is optional, so a response without one is parsed instead of raising a validation error.

## [1.0.2] - 2024-08-10

### Fixed

- `Cardinality.value` defaults to `None`, so an infinite cardinality, which carries no value, is parsed instead of raising a validation error.

## [1.0.1] - 2024-08-09

### Changed

- The README documents the full API.

## [1.0.0] - 2024-08-01

Initial release.

[1.1.0]: https://github.com/RegexSolver/regexsolver-python/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/RegexSolver/regexsolver-python/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/RegexSolver/regexsolver-python/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/RegexSolver/regexsolver-python/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/RegexSolver/regexsolver-python/releases/tag/v1.0.0
