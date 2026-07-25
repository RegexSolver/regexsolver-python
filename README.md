# RegexSolver Python API Client
[Homepage](https://regexsolver.com) | [Online Demo](https://regexsolver.com/demo) | [Documentation](https://docs.regexsolver.com) | [Developer Console](https://console.regexsolver.com)

**RegexSolver** is a powerful toolkit for building, combining, and analyzing regular expressions. It is designed for constraint solvers, test generators, and other systems that need advanced regex operations.

## Installation

```sh
pip install regexsolver
```

Requirements: **Python >= 3.9**

## Quick Start

1. Create an API token in the [Developer Console](https://console.regexsolver.com/).
2. Initialize the client and start working with terms.

### Synchronous Usage

The synchronous client provides a simple, blocking API.

```python
from regexsolver import RegexSolverClient, Term

client = RegexSolverClient("REGEXSOLVER_API_TOKEN")

term1 = Term.regex(r"(abc|de|fg){2,}")
term2 = Term.regex(r"de.*")

intersection = client.intersection(term1, term2)
pattern = client.get_pattern(intersection)
print(pattern)  # de(abc|de|fg)+
```

### Asynchronous Usage

For non-blocking applications, use the asynchronous client.

```python
import asyncio
from regexsolver import AsyncRegexSolverClient, Term

async def main():
    async with AsyncRegexSolverClient("REGEXSOLVER_API_TOKEN") as client:
        term1 = Term.regex(r"(abc|de|fg){2,}")
        term2 = Term.regex(r"de.*")

        intersection = await client.intersection(term1, term2)
        pattern = await client.get_pattern(intersection)
        print(pattern)  # de(abc|de|fg)+


asyncio.run(main())
```

## Key Concepts & Limitations

RegexSolver supports a subset of regular expressions that adhere to the principles of regular languages. Here are the key characteristics and limitations of the regular expressions supported by RegexSolver:
- **Anchored Expressions:** All regular expressions in RegexSolver are anchored. This means that the expressions are treated as if they start and end at the boundaries of the input text. For example, the expression `abc` will match the string "abc" but not "xabc" or "abcx".
- **Lookahead/Lookbehind:** RegexSolver does not support lookahead (`(?=...)`) or lookbehind (`(?<=...)`) assertions. Using them returns an error.
- **Pure Regular Expressions:** RegexSolver focuses on pure regular expressions as defined in regular language theory. This means features that extend beyond regular languages, such as backreferences (`\1`, `\2`, etc.), are not supported. Any use of backreference would return an error.
- **Greedy/Ungreedy Quantifiers:** The concept of ungreedy (`*?`, `+?`, `??`) quantifiers is not supported. All quantifiers are treated as greedy. For example, `a*` or `a*?` will match the longest possible sequence of "a"s.
- **Line Feed and Dot:** RegexSolver handles all characters the same way. The dot `.` matches any Unicode character including line feed (`\n`).
- **Empty Regular Expressions:** The empty language (matches no string) is represented by constructs like `[]` (empty character class). This is distinct from the empty string.

## Response Formats

The API can handle terms in two formats:
- `regex`: a regular expression pattern
- `fair`: FAIR (Fast Automaton Internal Representation), a stable, signed format used internally by the engine

By default, the engine returns whatever the operation produces, with no extra conversion. Override with `response_format`, accepted by the operations that return a term:

```python
from regexsolver import ResponseFormat

term1 = Term.regex(r"abcde")
term2 = Term.regex(r"de")

result = client.union(term1, term2, response_format=ResponseFormat.REGEX)
print(result)  # regex=(abc)?de

result = client.union(term1, term2, response_format=ResponseFormat.FAIR)
print(result)  # fair=...
```

If the format does not matter, omit `response_format` or set it to `ResponseFormat.ANY`.

Regardless of the format, you can always call `get_pattern()` to obtain the regex pattern of a term.

## Bounding execution time

Set a server-side compute timeout in milliseconds with `execution_timeout`:

```python
from regexsolver.exceptions import TimeoutExceededError

# Limit the server-side compute time to 100 ms
try:
    term1 = Term.regex(r".*ab.*c(de|fg).*dab.*c(de|fg).*ab.*c(de|fg).*dab.*c")
    term2 = Term.regex(r".*abc.*")
    
    res = client.difference(term1, term2, execution_timeout=100)
except TimeoutExceededError as error:
    print(error) # The API returned the following error: The operation took too much time.
```

Timeout is best effort. The exact time is not guaranteed.

## API Overview

`RegexSolverClient` and `AsyncRegexSolverClient` expose the following methods. Every method accepts optional keyword arguments: operations that return a term take `response_format`, `deterministic` and `execution_timeout`, while analyze operations and `determinize()` take `execution_timeout` only — the response format is not theirs to choose.

### Analyze

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.equivalent(term1, term2, **kwargs)` | `bool` | `True` if `term1` and `term2` accept exactly the same language. |
| `client.get_cardinality(term, **kwargs)` | `Cardinality` | Returns the number of possible matched strings. |
| `client.get_dot(term, **kwargs)` | `str` | Returns a Graphviz DOT representation of the automaton. |
| `client.get_length(term, **kwargs)` | `Length` | Returns the minimum and maximum length of matched strings. |
| `client.get_pattern(term, **kwargs)` | `str` | Returns a regular expression pattern for the term. |
| `client.is_empty(term, **kwargs)` | `bool` | `True` if the term matches no string. |
| `client.is_empty_string(term, **kwargs)` | `bool` | `True` if the term matches only the empty string. |
| `client.is_total(term, **kwargs)` | `bool` | `True` if the term matches all possible strings. |
| `client.is_deterministic(term, **kwargs)` | `bool` | `True` if the term's automaton is deterministic. Only a deterministic FAIR guarantees consistent string ordering across paginated `generate_strings()` calls; call `determinize()` first if this is `False`. |
| `client.subset(term1, term2, **kwargs)` | `bool` | `True` if every string matched by `term1` is also matched by `term2`. |

*Note: For `AsyncRegexSolverClient`, these methods are coroutines and must be awaited.*

### Compute

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.complement(term, **kwargs)` | `Term` | Computes the complement of the given term. |
| `client.concat(term1, term2, ..., **kwargs)` | `Term` | Concatenates multiple terms in order. |
| `client.determinize(term, **kwargs)` | `Term` | Computes a deterministic FAIR for the given term, suitable for consistent pagination with `generate_strings()`. |
| `client.difference(term1, term2, **kwargs)` | `Term` | Computes the difference `term1 - term2`. |
| `client.intersection(term1, term2, ..., **kwargs)` | `Term` | Computes the intersection of the given terms. |
| `client.repeat(term, min, max, **kwargs)` | `Term` | Computes the repetition of the term between `min` and `max` times. |
| `client.union(term1, term2, ..., **kwargs)` | `Term` | Computes the union of the given terms. |

*Note: For `AsyncRegexSolverClient`, these methods are coroutines and must be awaited.*

### Generate

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.generate_strings(term, limit, offset, **kwargs)` | `List[str]` | Generates up to `limit` unique strings matched by `term`, skipping the first `offset` strings. |

*Note: For `AsyncRegexSolverClient`, this method is a coroutine and must be awaited.*

## Cross-Language Support

If you want to use this library with other programming languages, we provide:
- [regexsolver-java](https://github.com/RegexSolver/regexsolver-java)
- [regexsolver-js](https://github.com/RegexSolver/regexsolver-js)

For more information about how to use the wrappers, you can refer to our [guide](https://docs.regexsolver.com/getting-started.html).

You can also take a look at [regexsolver](https://github.com/RegexSolver/regexsolver) which contains the source code of the engine.

## License

This project is licensed under the MIT License.
