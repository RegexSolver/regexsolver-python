# RegexSolver Python API Client

This repository contains the source code of the Python library for [RegexSolver](https://regexsolver.com) API.

RegexSolver is a powerful regular expression manipulation toolkit, that gives you the power to manipulate regex as if
they were sets.

## Installation

```sh
pip install --upgrade regexsolver
```

### Requirements

- Python >=3.7

## Usage

In order to use the library you need to generate an API Token on our [Developer Console](https://regexsolver.com/).

```python
from regexsolver import RegexSolver, Term

RegexSolver.initialize("YOUR TOKEN HERE")

term1 = Term.regex(r"(abc|de|fg){2,}")
term2 = Term.regex(r"de.*")
term3 = Term.regex(r".*abc")

term4 = Term.regex(r".+(abc|de).+")

result = term1.intersection(term2, term3)\
              .subtraction(term4)

print(result)
```
