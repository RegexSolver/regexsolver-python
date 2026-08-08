from dataclasses import dataclass
from typing import Optional

from regexsolver._generated.models import Length as GeneratedLength
from regexsolver.models.term_properties_mixin import TermPropertiesMixin


@dataclass
class Length(TermPropertiesMixin):
    """Represents the minimum and maximum lengths of any string matched by the term.

    Attributes:
        min (Optional[int]): The shortest possible matched string length, or None if the language is empty.
        max (Optional[int]): The longest possible matched string length, or None if the length is unbounded.
    """

    min: Optional[int]
    max: Optional[int]

    @classmethod
    def from_dto(cls, dto: GeneratedLength) -> "Length":
        """Converts a generated API model into a high-level Length object.

        Args:
            dto (GeneratedLength): The raw model from the generated API.

        Returns:
            Length: A high-level instance representing the min/max limits.
        """
        return cls(min=dto.min, max=dto.max)

    def __repr__(self) -> str:
        return f"<Length: min={self.min}, max={self.max}>"

    def is_empty(self) -> Optional[bool]:
        return self.min is None and self.max is None

    def is_empty_string(self) -> Optional[bool]:
        return self.min == 0 and self.max == 0

    def is_total(self) -> Optional[bool]:
        if self.min != 0 or self.max is not None:
            return False
        else:
            return None

    def is_infinite(self) -> bool:
        return self.min is not None and self.max is None
