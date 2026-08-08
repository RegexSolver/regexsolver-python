from enum import Enum


class PathOrder(str, Enum):
    """Order in which the paths of the language are scheduled when generating
    strings — the *shapes* the term allows, as opposed to the characters
    filling them.

    Attributes:
        SWEEP: Expand one path in full, shortest first, before moving to the
            next one. The cheapest way to page through a whole language.
        INTERLEAVE: Cover every path once before any path yields a second
            string. Best suited to deriving test cases.
        SHUFFLED: Interleave with same-length paths visited in an order drawn
            from the seed.
    """

    SWEEP = "sweep"
    INTERLEAVE = "interleave"
    SHUFFLED = "shuffled"

    def __str__(self) -> str:
        return str(self.value)


class CharacterOrder(str, Enum):
    """Order in which the strings within each path are produced when
    generating strings. Orthogonal to PathOrder: it does not change *what* can
    be generated, only which strings are reached first.

    Attributes:
        ASCENDING: Expand each position from the low end of its character
            range first — a stable order returning the smallest witnesses of a
            path first.
        SHUFFLED: A permutation drawn from the seed, so the strings look like
            real inputs. Random in look only — generation stays reproducible.
    """

    ASCENDING = "ascending"
    SHUFFLED = "shuffled"

    def __str__(self) -> str:
        return str(self.value)
