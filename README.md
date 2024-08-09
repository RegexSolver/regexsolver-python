# RegexSolver Python API Client
[Homepage](https://regexsolver.com) | [Documentation](https://docs.regexsolver.com) | [Developer Console](https://console.regexsolver.com)

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

In order to use the library you need to generate an API Token on our [Developer Console](https://console.regexsolver.com/).

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

## Features

- [Intersection](#intersection)
- [Union](#union)
- [Subtraction / Difference](#subtraction--difference)
- [Equivalence](#equivalence)
- [Subset](#subset)
- [Details](#details)
- [Generate Strings](#generate-strings)

### Intersection

#### Request

Compute the intersection of the provided terms and return the resulting term.

The maximum number of terms is currently limited to 10.

```python
term1 = Term.regex(r"(abc|de){2}")
term2 = Term.regex(r"de.*")
term3 = Term.regex(r".*abc")

result = term1.intersection(term2, term3)
print(result)
```

#### Response

```
regex=deabc
```

### Union

Compute the union of the provided terms and return the resulting term.

The maximum number of terms is currently limited to 10.

#### Request

```python
term1 = Term.regex(r"abc")
term2 = Term.regex(r"de")
term3 = Term.regex(r"fghi")

result = term1.union(term2, term3)
print(result)
```

#### Response

```
regex=(abc|de|fghi)
```

### Subtraction / Difference

Compute the first term minus the second and return the resulting term.

#### Request

```python
term1 = Term.regex(r"(abc|de)")
term2 = Term.regex(r"de")

result = term1.subtraction(term2)
print(result)
```

#### Response

```
regex=abc
```

### Equivalence

Analyze if the two provided terms are equivalent.

#### Request

```python
term1 = Term.regex(r"(abc|de)")
term2 = Term.regex(r"(abc|de)*")

result = term1.is_equivalent_to(term2)
print(result)
```

#### Response

```
False
```

### Subset

Analyze if the second term is a subset of the first.

#### Request

```java
term1 = Term.regex(r"de")
term2 = Term.regex(r"(abc|de)")

result = term1.is_subset_of(term2)
print(result)
```

#### Response

```
True
```

### Details

Compute the details of the provided term.

The computed details are:

- **Cardinality:** the number of possible values.
- **Length:** the minimum and maximum length of possible values.
- **Empty:** true if is an empty set (does not contain any value), false otherwise.
- **Total:** true if is a total set (contains all values), false otherwise.

#### Request

```python
term = Term.regex(r"(abc|de)")

details = term.get_details()
print(details)
```

#### Response

```
Details[cardinality=Integer(2), length=Length[minimum=2, maximum=3], empty=false, total=false]
```

### Generate Strings

Generate the given number of strings that can be matched by the provided term.

The maximum number of strings to generate is currently limited to 200.

#### Request

```python
term = Term.regex(r"(abc|de){2}")

strings = term.generate_strings(3)
print(strings)
```

#### Response

```
['deabc', 'abcde', 'dede']
```

