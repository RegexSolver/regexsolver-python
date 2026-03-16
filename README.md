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

The synchronous client is the easiest way to get started.

```python
from regexsolver import RegexSolverClient, Term

client = RegexSolverClient("YOUR_API_TOKEN")

term1 = Term.regex(r"(abc|de|fg){2,}")
term2 = Term.regex(r"de.*")

intersection = client.intersection(term1, term2)
pattern = client.get_pattern(intersection)
print(pattern)  # de(abc|de|fg)+
```

### Asynchronous Usage

For high-performance applications, use the asynchronous client.

```python
async def main():
    async with AsyncRegexSolverClient("YOUR_API_TOKEN") as client:
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

By default, the engine returns whatever the operation produces, with no extra convertion. Override with `response_format`:

```python
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
# Limit the server-side compute time to 100 ms
try:
    term1 = Term.regex(r".*ab.*c(de|fg).*dab.*c(de|fg).*ab.*c(de|fg).*dab.*c")
    term2 = Term.regex(r".*abc.*")
    
    res = client.difference(term1, term2, execution_timeout=100)
except TimeoutExceeded as error:
    print(error) # The API returned the following error: The operation took too much time.
```

Timeout is best effort. The exact time is not guaranteed.

## API Overview

`RegexSolverClient` and `AsyncRegexSolverClient` exposes the following methods.

### Analyze

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.equivalent(t1, t2)` | `bool` | `True` if `t1` and `t2` accept exactly the same language. |
| `client.get_cardinality(t)` | `Cardinality` | Returns the number of possible matched strings. |
| `client.get_dot(t)` | `str` | Returns a Graphviz DOT representation of the automaton. |
| `client.get_length(t)` | `Length` | Returns the minimum and maximum length of matched strings. |
| `client.get_pattern(t)` | `str` | Returns a regular expression pattern for the term. |
| `client.is_empty(t)` | `bool` | `True` if the term matches no string. |
| `client.is_empty_string(t)` | `bool` | `True` if the term matches only the empty string. |
| `client.is_total(t)` | `bool` | `True` if the term matches all possible strings. |
| `client.subset(t1, t2)` | `bool` | `True` if every string matched by `t1` is also matched by `t2`. |

### Compute

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.concat(*terms)` | `Term` | Concatenates multiple terms in order. |
| `client.difference(t1, t2)` | `Term` | Computes the difference `t1 - t2`. |
| `client.intersection(*terms)` | `Term` | Computes the intersection of the given terms. |
| `client.repeat(t, min, max)` | `Term` | Computes the repetition of the term between `min` and `max` times. |
| `client.union(*terms)` | `Term` | Computes the union of the given terms. |

### Generate

| Method | Return | Description |
| -------- | ------- | ------- |
| `client.generate_strings(t, count)` | `List[str]` | Generates up to `count` unique example strings matched by `t`. |

## Cross-Language Support

If you want to use this library with other programming languages, we provide:
- [regexsolver-java](https://github.com/RegexSolver/regexsolver-java)
- [regexsolver-js](https://github.com/RegexSolver/regexsolver-js)

For more information about how to use the wrappers, you can refer to our [guide](https://docs.regexsolver.com/getting-started.html).

You can also take a look at [regexsolver](https://github.com/RegexSolver/regexsolver) which contains the source code of the engine.

## License

This project is licensed under the MIT License.
