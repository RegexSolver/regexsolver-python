import asyncio
import logging
import threading
import weakref
from typing import List, Optional, Union

from regexsolver.clients.asynchronous import AsyncRegexSolverClient
from regexsolver.models.response_format import ResponseFormat
from regexsolver.models.term import Term

logger = logging.getLogger(__name__)

# Global state for the shared background event loop
_SHARED_LOOP: Optional[asyncio.AbstractEventLoop] = None
_SHARED_THREAD: Optional[threading.Thread] = None
_SHARED_LOCK = threading.Lock()


def _get_or_create_shared_loop() -> asyncio.AbstractEventLoop:
    """Retrieves the shared global event loop, creating and starting it if necessary."""
    global _SHARED_LOOP, _SHARED_THREAD
    with _SHARED_LOCK:
        if (
            _SHARED_LOOP is None
            or _SHARED_THREAD is None
            or not _SHARED_THREAD.is_alive()
        ):
            logger.debug("Starting shared RegexSolver background event loop thread.")
            _SHARED_LOOP = asyncio.new_event_loop()
            _SHARED_THREAD = threading.Thread(
                target=_SHARED_LOOP.run_forever,
                name="RegexSolverSyncWorker",
                daemon=True,
            )
            _SHARED_THREAD.start()
        return _SHARED_LOOP


class RegexSolverClient:
    """Synchronous Client for RegexSolver.

    Exposes all endpoints synchronously by managing a shared background event loop.
    While it supports manual `.close()`, it is best used as a context manager.
    """

    def __init__(self, api_token: str, base_url="https://api.regexsolver.com/v1"):
        logger.debug("Initializing RegexSolverClient.")
        self._loop = _get_or_create_shared_loop()
        self._aio = AsyncRegexSolverClient(api_token, base_url)

        # Ensure the async client is closed even if the user forgets to call close() or use 'with'
        self._finalizer = weakref.finalize(
            self, self._run_cleanup, self._aio, self._loop
        )

    @staticmethod
    def _run_cleanup(
        aio_client: AsyncRegexSolverClient, loop: asyncio.AbstractEventLoop
    ):
        """Finalizer callback to safely close the async client in the background loop."""
        if loop.is_running():
            logger.debug("Closing RegexSolverClient.")
            asyncio.run_coroutine_threadsafe(aio_client.aclose(), loop)

    def _run_sync(self, coro):
        """Helper to execute async methods safely from the sync wrapper."""
        # Use a longer timeout or allow it to be infinite since the server
        # already has its own execution_timeout logic.
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=None)

    def close(self):
        """Closes the underlying HTTP client session.

        The shared background thread remains running for other client instances.
        """
        if self._finalizer.detach():
            logger.debug("Closing RegexSolverClient.")
            self._run_sync(self._aio.aclose())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- ANALYZE ---
    def get_cardinality(self, term: Term, execution_timeout: Optional[int] = None):
        """Computes how many unique strings the term matches.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Cardinality: An object representing either an exact Integer, a BigInteger, or Infinite cardinality.
        """
        return self._run_sync(self._aio.get_cardinality(term, execution_timeout))

    def get_length(self, term: Term, execution_timeout: Optional[int] = None):
        """Computes the minimum and maximum length of strings matched by the term.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Length: An object containing `min` and `max` integers. Limits are `None` if unbounded or undefined.
        """
        return self._run_sync(self._aio.get_length(term, execution_timeout))

    def equivalent(
        self, term1: Term, term2: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Checks if the two terms accept exactly the same language.

        Args:
            term1: The first term.
            term2: The second term to compare against.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if they are entirely equivalent, False otherwise.
        """
        return self._run_sync(self._aio.equivalent(term1, term2, execution_timeout))

    def subset(
        self,
        term_subset: Term,
        term_superset: Term,
        execution_timeout: Optional[int] = None,
    ) -> bool:
        """Checks if the first term's language is a subset of the second term's language.

        Args:
            term_subset: The term to test as the subset.
            term_superset: The term representing the entire set space.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if every string matched by `term_subset` is also matched by `term_superset`.
        """
        return self._run_sync(
            self._aio.subset(term_subset, term_superset, execution_timeout)
        )

    def is_empty(self, term: Term, execution_timeout: Optional[int] = None) -> bool:
        """Checks if the term matches no strings at all.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the language is completely empty.
        """
        return self._run_sync(self._aio.is_empty(term, execution_timeout))

    def is_empty_string(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Checks if the term matches only the empty string.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the term strictly matches the empty string ("") and nothing else.
        """
        return self._run_sync(self._aio.is_empty_string(term, execution_timeout))

    def is_total(self, term: Term, execution_timeout: Optional[int] = None) -> bool:
        """Checks if the term matches all possible strings.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the term matches every possible strings.
        """
        return self._run_sync(self._aio.is_total(term, execution_timeout))

    def get_pattern(self, term: Term, execution_timeout: Optional[int] = None) -> str:
        """Returns a regular expression pattern that represents the term.

        Args:
            term: The term to extract the pattern from.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            str: A valid regular expression string representing the language.
        """
        return self._run_sync(self._aio.get_pattern(term, execution_timeout))

    def get_dot(self, term: Term, execution_timeout: Optional[int] = None) -> str:
        """Builds a Graphviz DOT representation of the term's automaton.

        Args:
            term: The term to visualize.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            str: The raw DOT syntax for Graphviz compilation.
        """
        return self._run_sync(self._aio.get_dot(term, execution_timeout))

    # --- COMPUTE ---
    def concat(
        self,
        *terms: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Concatenates the given terms sequentially.

        Args:
            *terms: A dynamic list of terms to concatenate in order.
            response_format: The return format of the term (any, regex or fair).
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A newly computed concatenated term.
        """
        return self._run_sync(
            self._aio.concat(
                *terms,
                response_format=response_format,
                execution_timeout=execution_timeout,
            )
        )

    def intersection(
        self,
        *terms: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the intersection of the given terms.

        Args:
            *terms: A dynamic list of terms to intersect.
            response_format: The return format of the term (any, regex or fair).
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A term representing only strings matched by ALL provided terms.
        """
        return self._run_sync(
            self._aio.intersection(
                *terms,
                response_format=response_format,
                execution_timeout=execution_timeout,
            )
        )

    def union(
        self,
        *terms: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the union of the given terms.

        Args:
            *terms: A dynamic list of terms to combine.
            response_format: The return format of the term (any, regex or fair).
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A term representing strings matched by ANY of the provided terms.
        """
        return self._run_sync(
            self._aio.union(
                *terms,
                response_format=response_format,
                execution_timeout=execution_timeout,
            )
        )

    def difference(
        self,
        base_term: Term,
        excluded_term: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the difference between the two provided terms.

        Args:
            base_term: The base language term to subtract from.
            excluded_term: The term whose language should be removed from the base.
            response_format: The return format of the term (any, regex or fair).
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A computed difference term.
        """
        return self._run_sync(
            self._aio.difference(
                base_term,
                excluded_term,
                response_format=response_format,
                execution_timeout=execution_timeout,
            )
        )

    def repeat(
        self,
        term: Term,
        min_val: int,
        max_val: Optional[int] = None,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Repeats a term between a minimum and maximum number of times.

        Args:
            term: The term to repeat.
            min_val: The inclusive lower bound of repetitions.
            max_val: The inclusive upper bound. If None, repetitions are unbounded.
            response_format: The return format of the term (any, regex or fair).
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A computed repeated term.
        """
        return self._run_sync(
            self._aio.repeat(
                term,
                min_val,
                max_val,
                response_format=response_format,
                execution_timeout=execution_timeout,
            )
        )

    # --- GENERATE ---
    def generate_strings(
        self,
        term: Term,
        count: int,
        offset: int,
        execution_timeout: Optional[int] = None,
    ) -> List[str]:
        """Generates up to `count` distinct strings matched by 'term', skipping the first 'offset' strings.

        Args:
            term: The term to sample generated strings from.
            count: The maximum number of unique strings to return.
            offset: Number of matched strings to skip before starting to collect the results. Used for pagination.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            List[str]: A list of strings that match the term.
        """
        return self._run_sync(
            self._aio.generate_strings(term, count, offset, execution_timeout)
        )
