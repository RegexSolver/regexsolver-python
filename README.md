# RegexSolver Python API Client
[Homepage](https://regexsolver.com) | [Online Demo](https://regexsolver.com/demo) | [Documentation](https://docs.regexsolver.com) | [Developer Console](https://console.regexsolver.com)

Python client for the RegexSolver API.

RegexSolver is a powerful regular expression manipulation toolkit, that gives you the power to manipulate regex as if
they were sets.

## Installation

```sh
pip install --upgrade regexsolver
```
Requirements: Python >= 3.7

## Quick Start

1. Create an API token in the [Developer Console](https://console.regexsolver.com/).
2. Initialize the client and start working with terms:

```python
from regexsolver import RegexSolver, Term

# Set REGEXSOLVER_API_TOKEN in your env and call initialize(),
# or pass the token directly:
RegexSolver.initialize()  # or RegexSolver.initialize("YOUR_API_TOKEN")

# Create terms
term1 = Term.regex(r"(abc|de|fg){2,}")
term2 = Term.regex(r"de.*")
term3 = Term.regex(r".*abc")

# Compute intersection and difference
result = term1.intersection(term2, term3).difference(
    Term.regex(r".+(abc|de).+")
)

print(result.get_pattern())  # de(fg)*abc
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
from regexsolver import RegexSolver, ResponseFormat, Term

term = Term.regex(r"abcde")
result = term.union(Term.regex(r"de"), response_format=ResponseFormat.REGEX)
print(result)  # regex=(abc)?de

result = term.intersection(Term.regex(r"de.*"), response_format=ResponseFormat.FAIR)
print(result)  # fair=...
```

If the format does not matter, omit `response_format` or set it to `ResponseFormat.ANY`.

Regardless of internal format, you can call `get_pattern()` to obtain a regex string.

## Bounding execution time

Set a server-side compute timeout in milliseconds with `execution_timeout`:

```python
from regexsolver import ApiError, RegexSolver, Term

# Limit the server-side compute time to 5 ms
try:
    res = Term.regex(r".*ab.*c(de|fg).*dab.*c(de|fg).*ab.*c(de|fg).*dab.*c").difference(
        Term.regex(r".*abc.*"),
        execution_timeout=5
    )
except ApiError as error:
    print(error) # The API returned the following error: The operation took too much time.
```

Timeout is best effort. The exact time is not guaranteed.

## API Overview

`Term` exposes the following methods.

### Build
| Method | Return | Description |
| -------- | ------- | ------- |
| `Term.fair(fair: str)` | `Term` | Creates a term from a FAIR. |
| `Term.regex(regex: str)` | `Term` | Creates a term from a regex pattern. |

### Analyze

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.equivalent(term: Term)` | `bool` | `True` if `t` and `term` accept exactly the same language. Supports `execution_timeout`. |
| `t.get_cardinality()` | `Cardinality` | Returns the cardinality of the term (i.e., the number of possible matched strings). |
| `t.get_details()` | `Details` | Returns cardinality, length bounds, and if it is empty or total. |
| `t.get_dot()` | `str` | Returns a Graphviz DOT representation of the automaton for the term. |
| `t.get_fair()` | `str` | Returns the FAIR of the term if defined. |
| `t.get_length()` | `Length` | Returns the minimum and maximum length of matched strings. |
| `t.get_pattern()` | `str` | Returns a regular expression pattern for the term. |
| `t.is_empty()` | `bool` | `True` if the term matches no string. |
| `t.is_empty_string()` | `bool` | `True` if the term matches only the empty string. |
| `t.is_total()` | `bool` | `True` if the term matches all possible strings. |
| `t.subset(term: Term)` | `bool` | `True` if every string matched by `t` is also matched by `term`. Supports `execution_timeout`. |

### Compute

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.concat(*terms: Term)` | `Term` | Concatenates `t` with the given terms. Supports `response_format` and `execution_timeout`. |
| `t.difference(term: Term)` | `Term` | Computes the difference `t - term`. Supports `response_format` and `execution_timeout`. |
| `t.intersection(*terms: Term)` | `Term` | Computes the intersection of `t` with the given terms. Supports `response_format` and `execution_timeout`. |
| `t.repeat(min: int, max: Optional[int])` | `Term` | Computes the repetition of the term between `min` and `max` times; if `max` is `None`, the repetition is unbounded. Supports `response_format` and `execution_timeout`. |
| `t.union(*terms: Term)` | `Term` | Computes the union of `t` with the given terms. Supports `response_format` and `execution_timeout`. |

### Generate

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.generate_strings(count: int)` | `List[str]` | Generates up to `count` unique example strings matched by `t`. Supports `execution_timeout`. |

### Other
| Method | Return | Description |
| -------- | ------- | ------- |
| `t.serialize()` | `str` | Returns a serialized form of `t`. |
| `Term.deserialize(string: str)` | `Term` | Returns a deserialized term from the given `string`. |

## Cross-Language Support

If you want to use this library with other programming languages, we provide:
- [regexsolver-java](https://github.com/RegexSolver/regexsolver-java)
- [regexsolver-js](https://github.com/RegexSolver/regexsolver-js)

For more information about how to use the wrappers, you can refer to our [guide](https://docs.regexsolver.com/getting-started.html).

You can also take a look at [regexsolver](https://github.com/RegexSolver/regexsolver) which contains the source code of the engine.

## License

This project is licensed under the MIT License.
