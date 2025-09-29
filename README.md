# RegexSolver Python API Client
[Homepage](https://regexsolver.com) | [Online Demo](https://regexsolver.com/demo) | [Documentation](https://docs.regexsolver.com) | [Developer Console](https://console.regexsolver.com)

This repository contains the source code of the Python library for [RegexSolver](https://regexsolver.com) API.

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
from regexsolver import RegexSolver, ResponseFormat, Term

# Initialize with your API token
RegexSolver.initialize("YOUR_API_TOKEN")

# Create terms
term1 = Term.regex(r"(abc|de|fg){2,}")
term2 = Term.regex(r"de.*")
term3 = Term.regex(r".*abc")

# Compute intersection and difference
result = term1.intersection(term2, term3, response_format="regex").difference(
    Term.regex(r".+(abc|de).+"), response_format=ResponseFormat.REGEX
)

print(result)  # regex=deabc
```

## Key Concepts & Limitations

RegexSolver supports a subset of regular expressions that adhere to the principles of regular languages. Here are the key characteristics and limitations of the regular expressions supported by RegexSolver:
- **Anchored Expressions:** All regular expressions in RegexSolver are anchored. This means that the expressions are treated as if they start and end at the boundaries of the input text. For example, the expression `abc` will match the string "abc" but not "xabc" or "abcx".
- **Lookahead/Lookbehind:** RegexSolver does not support lookahead (`(?=...)`) or lookbehind (`(?<=...)`) assertions. Using them returns an error.
- **Pure Regular Expressions:** RegexSolver focuses on pure regular expressions as defined in regular language theory. This means features that extend beyond regular languages, such as backreferences (`\1`, `\2`, etc.), are not supported. Any use of backreference would return an error.
- **Greedy/Ungreedy Quantifiers:** The concept of ungreedy (`*?`, `+?`, `??`) quantifiers is not supported. All quantifiers are treated as greedy. For example, `a*` or `a*?` will match the longest possible sequence of "a"s.
- **Line Feed and Dot:** RegexSolver handles all characters the same way. The dot `.` matches any Unicode character including line feed (`\n`).
- **Empty Regular Expressions:** The empty language (matches no string) is represented by constructs like `[]` (empty character class). This is distinct from the empty string.

RegexSolver is based on the [regex-syntax](https://docs.rs/regex-syntax/0.8.5/regex_syntax/) library for parsing patterns. Unsupported features are parsed but ignored; they do not raise an error unless they affect semantics that cannot be represented (e.g., backreferences). This allows for some flexibility in writing regular expressions, but it is important to be aware of the unsupported features to avoid unexpected behavior.

## Response formats

The API can handle terms in two formats:
- `regex`: a regular expression pattern
- `fair`: FAIR (Fast Automaton Internal Representation); a representation used internally by the RegexSolver engine.

For some operations returning a FAIR is cheaper for the engine. If you do not force a format, it will choose the most suitable one. To control the output, pass `response_format`:

```python
from regexsolver import RegexSolver, ResponseFormat, Term

term = Term.regex(r"(ab|c){2}")
u = term.union(Term.regex(r"de"), response_format=ResponseFormat.REGEX)
print(u)  # regex=((c|ab){2}|de)

i = term.intersection(Term.regex(r"de.*"), response_format=ResponseFormat.FAIR)
print(i)  # fair=...
```

If the response format does not matter the argument `response_format` can be omitted or its value can be set to `ResponseFormat.ANY`.

## Bounding execution time

Long computations can be bounded with `execution_timeout` (milliseconds). Most methods on Term accepts it:

```python
# Limit the server-side compute time to 300 ms
res = Term.regex(r"(a|b){100}").intersection(
    Term.regex(r"a+"),
    execution_timeout=300
)
```
If time is exceeded, the API will return an error. Catch `ApiError` to handle it.

## API Overview

The client exposes three main groups of operations:

### Analyze

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.get_details()` | `Details` | Return cardinality, length bounds, and if it is empty or total. |
| `t.get_cardinality()` | `Cardinality` | Returns the cardinality of the term (i.e., the number of possible matched strings). |
| `t.get_length()` | `Length` | Returns the minimum and maximum length of matched strings. |
| `t.is_empty()` | `bool` | `True` if the term matches no string. |
| `t.is_total()` | `bool` | `True` if the term matches all possible strings. |
| `t.is_empty_string()` | `bool` | `True` if the term matches only the empty string. |
| `t.equivalent(term: Term)` | `bool` | `True` if `t` and `term` accept exactly the same language. Supports `execution_timeout`. |
| `t.subset(term: Term)` | `bool` | `True` if every string matched by `t` is also matched by `term`. Supports `execution_timeout`. |
| `t.get_dot()` | `str` | Return a GraphViz DOT representation of the automaton for the term. |
| `t.get_pattern()` | `str` | Return a regular expression pattern for the term. |

### Compute

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.concat(*terms: Term)` | `Term` | Concatenate `t` with the given terms. Supports `response_format` and `execution_timeout`. |
| `t.union(*terms: Term)` | `Term` | Compute the union of `t` with the given terms. Supports `response_format` and `execution_timeout`. |
| `t.intersection(*terms: Term)` | `Term` | Compute the intersection of `t` with the given terms. Supports `response_format` and `execution_timeout`. |
| `t.difference(term: Term)` | `Term` | Compute the difference `t - term`. Supports `response_format` and `execution_timeout`. |
| `t.repeat(min: int, max: Optional[int])` | `Term` | Computes the repetition of the term between `min` and `max` times; if `max` is `None`, the repetition is unbounded. Supports `response_format` and `execution_timeout`. |

### Generate

| Method | Return | Description |
| -------- | ------- | ------- |
| `t.generate_strings(count: int)` | `List[str]` | Generate up to `count` unique example strings matched by `t`. Supports `execution_timeout`. |

## Cross-Language Support

If you want to use this library with other programming languages, we provide a wide range of wrappers:
- [regexsolver-java](https://github.com/RegexSolver/regexsolver-java)
- [regexsolver-js](https://github.com/RegexSolver/regexsolver-js)

For more information about how to use the wrappers, you can refer to our [guide](https://docs.regexsolver.com/getting-started.html).

If you want to run the engine yourself you can also take a look at [regexsolver](https://github.com/RegexSolver/regexsolver).

## License

This project is licensed under the MIT License.
