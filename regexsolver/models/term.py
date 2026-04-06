import re
from abc import ABC, abstractmethod
from re import Pattern
from typing import Any, Optional

from regexsolver._generated.models import Term as GeneratedTerm
from regexsolver._generated.models.term_fair import TermFair
from regexsolver._generated.models.term_regex import TermRegex
from regexsolver.models.cardinality import Cardinality
from regexsolver.models.length import Length
from regexsolver.models.term_properties_mixin import TermPropertiesMixin


class Term(ABC):
    """Represents a mathematical term (Regex or FAIR) on which operations can be performed."""

    def __init__(self, value: str):
        self._value = value

        # Shared Cache (Internal)
        self._cardinality: Optional[Cardinality] = None
        self._length: Optional[Length] = None
        self._empty: Optional[bool] = None
        self._empty_string: Optional[bool] = None
        self._total: Optional[bool] = None
        self._pattern: Optional[str] = None
        self._dot: Optional[str] = None
        self._stable_term: Optional["Term"] = None

        self._compiled_regex: Optional[Pattern] = None

    @abstractmethod
    def get_pattern(self) -> Optional[str]:
        pass

    @abstractmethod
    def get_fair(self) -> Optional[str]:
        pass

    @abstractmethod
    def to_dto(self) -> GeneratedTerm:
        pass

    @abstractmethod
    def serialize(self) -> str:
        pass

    @classmethod
    def regex(cls, pattern: str) -> "Term":
        return RegexTerm(pattern)

    @classmethod
    def fair(cls, payload: str) -> "Term":
        return FairTerm(payload)

    # --- Shared Behavior ---

    def get_value(self) -> str:
        return self._value

    def _set_properties_mixin(self, properties_mixin: TermPropertiesMixin):
        empty = properties_mixin.is_empty()
        if empty is not None:
            self._empty = empty

        empty_string = properties_mixin.is_empty_string()
        if empty_string is not None:
            self._empty_string = empty_string

        total = properties_mixin.is_total()
        if total is not None:
            self._total = total

    def is_match(self, string: str) -> bool:
        """Client-side matching implementation."""
        pattern = self.get_pattern()
        if pattern is None:
            raise RuntimeError(
                "The regex pattern of this term is not defined yet, call get_pattern() on the client to set it."
            )

        if self._compiled_regex is None:
            try:
                self._compiled_regex = re.compile(rf"\A(?:{pattern})\Z", re.DOTALL)
            except re.error as e:
                raise ValueError(
                    f"Invalid regular expression for Python's `re` engine: {pattern}"
                ) from e

        return self._compiled_regex.match(string) is not None

    @classmethod
    def deserialize(cls, serialized: str) -> Optional["Term"]:
        if not serialized or "=" not in serialized:
            return None

        index = serialized.find("=")
        type_str = serialized[:index]
        val = serialized[index + 1 :]

        if type_str.lower() == "regex":
            return cls.regex(val)
        elif type_str.lower() == "fair":
            return cls.fair(val)

        return None

    @classmethod
    def from_dto(cls, dto: GeneratedTerm) -> "Term":
        actual_instance = dto.actual_instance
        if actual_instance is None:
            raise RuntimeError("Invalid Term DTO provided.")
        if actual_instance.type == "regex":
            return cls.regex(actual_instance.value)
        else:
            return cls.fair(actual_instance.value)

    # --- Shared Getters/Setters ---

    def get_cached_stable_term(self) -> Optional["Term"]:
        return self._stable_term

    def set_cached_stable_term(self, stable_term: Optional["Term"]):
        self._stable_term = stable_term

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, Term):
            return False
        return self.serialize() == other.serialize()

    def __hash__(self) -> int:
        return hash(self.serialize())

    def __str__(self) -> str:
        return self.serialize()

    def __repr__(self) -> str:
        return self.serialize()


class RegexTerm(Term):
    def get_pattern(self) -> Optional[str]:
        return self.get_value()

    def get_fair(self) -> Optional[str]:
        stable = self.get_cached_stable_term()
        return stable.get_fair() if stable else None

    def to_dto(self) -> GeneratedTerm:
        return GeneratedTerm(TermRegex(type="regex", value=self.get_value()))

    def serialize(self) -> str:
        return f"regex={self.get_value()}"


class FairTerm(Term):
    def get_pattern(self) -> Optional[str]:
        return self._pattern

    def get_fair(self) -> Optional[str]:
        return self.get_value()

    def to_dto(self) -> GeneratedTerm:
        return GeneratedTerm(TermFair(type="fair", value=self.get_value()))

    def serialize(self) -> str:
        return f"fair={self.get_value()}"
