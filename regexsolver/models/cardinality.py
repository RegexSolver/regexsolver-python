from dataclasses import dataclass
from typing import Optional, cast

from regexsolver._generated.models import Cardinality as GeneratedCardinality
from regexsolver.models.term_properties_mixin import TermPropertiesMixin


class Cardinality(TermPropertiesMixin):
    """Base class representing the number of unique strings matched by a term."""

    @classmethod
    def from_dto(cls, dto: GeneratedCardinality) -> "Cardinality":
        """Converts a generated API model into a high-level Cardinality object.

        Args:
            dto (GeneratedCardinality): The raw model from the generated API.

        Returns:
            Cardinality: A specialized instance (Integer, BigInteger, or Infinite).

        Raises:
            ValueError: If the DTO contains an unknown cardinality type.
        """
        actual_model = getattr(dto, "actual_instance", dto)
        c_type = actual_model.type

        if c_type == "infinite":
            return Infinite()
        elif c_type == "bigInteger":
            return BigInteger()
        elif c_type == "integer":
            return Integer(actual_model.value)
        else:
            raise ValueError(f"Unknown cardinality type: {c_type}")

    def __repr__(self) -> str:
        return "<Cardinality>"


@dataclass(frozen=True)
class Infinite(Cardinality):
    """Indicates that the set of matched strings is infinite."""

    def is_empty(self) -> Optional[bool]:
        return False

    def is_empty_string(self) -> Optional[bool]:
        return False

    def __repr__(self) -> str:
        return "<Cardinality::Infinite>"


@dataclass(frozen=True)
class BigInteger(Cardinality):
    """Indicates that the set of matched strings is finite but too large to be returned as a standard integer."""

    def is_empty(self) -> Optional[bool]:
        return False

    def is_empty_string(self) -> Optional[bool]:
        return False

    def is_total(self) -> Optional[bool]:
        return False

    def __repr__(self) -> str:
        return "<Cardinality::BigInteger>"


@dataclass(frozen=True)
class Integer(Cardinality):
    """Indicates that the set of matched strings is finite and exactly calculable.

    Attributes:
        value (int): The exact count of uniquely matched strings.
    """

    value: int

    def is_empty(self) -> bool:
        return self.value == 0

    def is_empty_string(self) -> Optional[bool]:
        if self.value == 1:
            return None
        return False

    def is_total(self) -> Optional[bool]:
        return False

    def __repr__(self) -> str:
        return f"<Cardinality::Integer({self.value})>"
