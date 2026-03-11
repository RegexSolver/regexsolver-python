from typing import Optional


class TermPropertiesMixin:
    """A mixin providing default property inference for Term analytics.

    Returns `None` when a property cannot be strictly inferred from the current data alone.
    """

    def is_empty(self) -> Optional[bool]:
        """Infers whether the term matches no strings at all.

        Returns:
            Optional[bool]: True if it definitely matches no strings, False if it matches at least one, or None if it cannot be inferred.
        """
        return None

    def is_empty_string(self) -> Optional[bool]:
        """Infers whether the term matches strictly the empty string ("").

        Returns:
            Optional[bool]: True if it definitely matches only the empty string, False if it matches other strings, or None if it cannot be inferred.
        """
        return None

    def is_total(self) -> Optional[bool]:
        """Infers whether the term matches all possible strings.

        Returns:
            Optional[bool]: True if it definitely matches all strings, False if it misses at least one string, or None if it cannot be inferred.
        """
        return None
