import pytest

from regexsolver.generated.models import Cardinality as GeneratedCardinality
from regexsolver.generated.models import (
    CardinalityBigInteger,
    CardinalityInfinite,
    CardinalityInteger,
    TermFair,
    TermRegex,
)
from regexsolver.generated.models import Length as GeneratedLength
from regexsolver.generated.models import Term as GeneratedTerm
from regexsolver.models.cardinality import BigInteger, Cardinality, Infinite, Integer
from regexsolver.models.length import Length
from regexsolver.models.term import FairTerm, RegexTerm, Term


def test_term_creation_regex():
    term = Term.regex("abc")
    assert isinstance(term, RegexTerm)
    assert term.get_value() == "abc"
    assert isinstance(term.to_dto(), GeneratedTerm)


def test_term_creation_fair():
    term = Term.fair("fair_payload")
    assert isinstance(term, FairTerm)
    assert term.get_value() == "fair_payload"


def test_term_from_dto_regex():
    gen_term = GeneratedTerm(TermRegex(type="regex", value="abc"))
    term = Term.from_dto(gen_term)
    assert isinstance(term, RegexTerm)
    assert term.get_value() == "abc"


def test_term_from_dto_fair():
    gen_term = GeneratedTerm(TermFair(type="fair", value="payload"))
    term = Term.from_dto(gen_term)
    assert isinstance(term, FairTerm)
    assert term.get_value() == "payload"


def test_cardinality_integer():
    c = Integer(10)
    assert c.value == 10
    assert c.is_empty() is False
    assert c.is_empty_string() is False
    assert c.is_total() is False
    assert repr(c) == "<Cardinality::Integer(10)>"


def test_cardinality_from_dto_integer():
    gen_card = GeneratedCardinality(CardinalityInteger(type="integer", value=10))
    c = Cardinality.from_dto(gen_card)
    assert isinstance(c, Integer)
    assert c.value == 10


def test_cardinality_from_dto_big_integer():
    gen_card = GeneratedCardinality(CardinalityBigInteger(type="bigInteger"))
    c = Cardinality.from_dto(gen_card)
    assert isinstance(c, BigInteger)


def test_cardinality_from_dto_infinite():
    gen_card = GeneratedCardinality(CardinalityInfinite(type="infinite"))
    c = Cardinality.from_dto(gen_card)
    assert isinstance(c, Infinite)


def test_cardinality_integer_zero():
    c = Integer(0)
    assert c.is_empty() is True
    assert c.is_empty_string() is False


def test_cardinality_integer_one():
    c = Integer(1)
    assert c.is_empty() is False
    assert c.is_empty_string() is None  # Per implementation


def test_cardinality_big_integer():
    c = BigInteger()
    assert c.is_empty() is False
    assert c.is_empty_string() is False
    assert c.is_total() is False
    assert repr(c) == "<Cardinality::BigInteger>"


def test_cardinality_infinite():
    c = Infinite()
    assert c.is_empty() is False
    assert c.is_empty_string() is False
    assert repr(c) == "<Cardinality::Infinite>"


def test_length():
    length = Length(min=1, max=5)
    assert length.min == 1
    assert length.max == 5
    assert length.is_empty() is False
    assert length.is_empty_string() is False
    assert length.is_total() is False
    assert repr(length) == "<Length: min=1, max=5>"


def test_length_from_dto():
    gen_len = GeneratedLength(type="length", min=1, max=5)
    length_obj = Length.from_dto(gen_len)
    assert length_obj.min == 1
    assert length_obj.max == 5


def test_length_empty():
    length = Length(min=None, max=None)
    assert length.is_empty() is True


def test_length_empty_string():
    length = Length(min=0, max=0)
    assert length.is_empty_string() is True


def test_length_total_candidate():
    length = Length(min=0, max=None)
    assert length.is_total() is None  # Implementation returns None if it COULD be total


def test_term_properties_caching():
    term = Term.regex("abc")
    assert term._cardinality is None

    c = Integer(5)
    term._cardinality = c
    # Simulate AsyncRegexSolverClient behavior
    term._set_properties_mixin(c)

    assert term._cardinality == c
    # Since Integer(5).is_empty() is False, it should set _empty to False
    assert term._empty is False


def test_term_get_fair_and_pattern():
    regex_term = Term.regex("abc")
    assert regex_term.get_pattern() == "abc"
    assert regex_term.get_fair() is None

    fair_term = Term.fair("payload")
    assert fair_term.get_fair() == "payload"
    assert fair_term.get_pattern() is None

    fair_term._pattern = "abc"
    assert fair_term.get_pattern() == "abc"


def test_term_serialize_deserialize():
    term = Term.regex("abc")
    serialized = term.serialize()
    assert serialized == "regex=abc"
    assert str(term) == "regex=abc"

    deserialized = Term.deserialize(serialized)
    assert deserialized == term
    assert hash(deserialized) == hash(term)

    fair_term = Term.fair("payload")
    assert Term.deserialize(fair_term.serialize()) == fair_term

    assert Term.deserialize("invalid") is None
    assert Term.deserialize("unknown=value") is None


def test_term_is_match():
    term = Term.regex("a.b")
    assert term.is_match("axb") is True
    assert term.is_match("a\nb") is True  # DOTALL
    assert term.is_match("ab") is False
    assert term.is_match("axxb") is False  # anchored (fullmatch)

    fair_term = Term.fair("payload")
    # Matches the new Java-aligned behavior of throwing an exception
    with pytest.raises(RuntimeError, match="not defined yet"):
        fair_term.is_match("abc")
