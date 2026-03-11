from dataclasses import dataclass
from typing import Optional

from regexsolver.models.term_properties_mixin import TermPropertiesMixin


class Cardinality(TermPropertiesMixin):
    """Base class representing the number of unique strings matched by a term."""

    pass


@dataclass(frozen=True)
class Infinite(Cardinality):
    """Indicates that the set of matched strings is infinite."""

    def is_empty(self) -> Optional[bool]:
        return False

    def is_empty_string(self) -> Optional[bool]:
        return False


@dataclass(frozen=True)
class BigInteger(Cardinality):
    """Indicates that the set of matched strings is finite but too large to be returned as a standard integer."""

    def is_empty(self) -> Optional[bool]:
        return False

    def is_empty_string(self) -> Optional[bool]:
        return False

    def is_total(self) -> Optional[bool]:
        return False


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
