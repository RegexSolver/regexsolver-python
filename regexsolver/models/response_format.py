from enum import Enum


class ResponseFormat(str, Enum):
    """Defines the format in which the engine should return computed Terms.

    Attributes:
        ANY: Allows the engine to return the result in the most efficient format.
        FAIR: Fast Automaton Internal Representation, a stable internal format.
        REGEX: Standard regular expression pattern.
    """

    ANY = "any"
    FAIR = "fair"
    REGEX = "regex"

    def __str__(self) -> str:
        return str(self.value)
