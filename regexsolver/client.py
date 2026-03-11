import asyncio
import threading
import time
from typing import List, Optional, Union

from regexsolver.exceptions import ApiError
from regexsolver.generated import (
    ApiException,
    ErrorResponse,
    ExecutionOptions,
    ResponseOptions,
    TwoTermsRequest,
)
from regexsolver.generated.api.analyze_api import AnalyzeApi
from regexsolver.generated.api.compute_api import ComputeApi
from regexsolver.generated.api.generate_api import GenerateApi
from regexsolver.generated.api_client import ApiClient
from regexsolver.generated.configuration import Configuration
from regexsolver.generated.models import (
    GenerateStringsRequest,
    MultiTermsRequest,
    RepeatRequest,
    RequestOptions,
    TermRequest,
)
from regexsolver.models.cardinality import BigInteger, Infinite, Integer
from regexsolver.models.length import Length
from regexsolver.models.response_format import ResponseFormat
from regexsolver.models.term import Term


class AsyncRegexSolverClient:
    """The Asynchronous Client for RegexSolver.

    Provides non-blocking access to all RegexSolver API endpoints.
    Should be instantiated using an `async with` context manager.
    """

    def __init__(self, api_token: str, base_url="https://api.regexsolver.com/v1"):
        self.configuration = Configuration(host=base_url, access_token=api_token)
        self.api_client = ApiClient(self.configuration)
        self.api_client.user_agent = "RegexSolver Python / 1.1.0"

        self._analyze_api = AnalyzeApi(self.api_client)
        self._compute_api = ComputeApi(self.api_client)
        self._generate_api = GenerateApi(self.api_client)

        self._lock = asyncio.Lock()
        self._resume_time = 0.0

    async def aclose(self):
        """Closes the underlying HTTP client session."""
        await self.api_client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    # --- HELPER ---
    async def _execute_with_retry(self, api_method, **kwargs):
        max_retries = 5
        retries = 0

        while True:
            async with self._lock:
                sleep_time = self._resume_time - time.time()

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            try:
                return await api_method(**kwargs)

            except ApiException as e:
                if e.status == 429:
                    retries += 1
                    if retries > max_retries:
                        raise ApiError(
                            "Max retries exceeded for 429 Too Many Requests.",
                            status_code=429,
                        )

                    async with self._lock:
                        sleep_time = self._resume_time - time.time()
                        if sleep_time <= 0:
                            headers = e.headers or {}
                            retry_after = int(headers.get("Retry-After", 1))
                            self._resume_time = time.time() + retry_after
                            sleep_time = retry_after

                    await asyncio.sleep(sleep_time)
                    continue

                error_msg = e.reason

                if e.body:
                    try:
                        parsed_error = ErrorResponse.from_json(e.body)
                        if parsed_error is not None:
                            error_msg = parsed_error.error
                        else:
                            error_msg = e.body
                    except Exception:
                        error_msg = e.body

                error_msg = str(error_msg) if error_msg else "Unknown API Error"
                raise ApiError(error_msg, status_code=e.status, body=e.body) from None

    def _build_options(
        self,
        execution_timeout: Optional[int] = None,
        response_format: Optional[Union[ResponseFormat, str]] = None,
    ) -> RequestOptions:
        options = RequestOptions(schemaVersion=1)
        if execution_timeout:
            options.execution = ExecutionOptions(timeout=execution_timeout)
        if response_format:
            options.response = ResponseOptions(format=response_format)
        return options

    # --- ANALYZE ---
    async def get_cardinality(
        self, term: Term, execution_timeout: Optional[int] = None
    ):
        """Computes how many unique strings the term matches.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Cardinality: An object representing either an exact Integer, a BigInteger, or Infinite cardinality.
        """
        if term._cardinality is not None:
            return term._cardinality

        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.cardinality, term_request=request
        )

        generated_cardinality = response.data
        actual_model = getattr(
            generated_cardinality, "actual_instance", generated_cardinality
        )

        c_type = actual_model.type
        if c_type == "infinite":
            term._cardinality = Infinite()
        elif c_type == "bigInteger":
            term._cardinality = BigInteger()
        elif c_type == "integer":
            term._cardinality = Integer(actual_model.value)
        else:
            raise ValueError(f"Unknown cardinality type: {c_type}")

        term._set_properties_mixin(term._cardinality)
        return term._cardinality

    async def get_length(self, term: Term, execution_timeout: Optional[int] = None):
        """Computes the minimum and maximum length of strings matched by the term.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Length: An object containing `min` and `max` integers. Limits are `None` if unbounded or undefined.
        """
        if term._length is not None:
            return term._length

        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.length, term_request=request
        )

        generated_length = response.data
        term._length = Length(min=generated_length.min, max=generated_length.max)
        term._set_properties_mixin(term._length)
        return term._length

    async def equivalent(
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
        request = TwoTermsRequest(
            terms=[term1._api_model, term2._api_model],
            options=self._build_options(execution_timeout),
        )
        response = await self._execute_with_retry(
            self._analyze_api.equivalent, two_terms_request=request
        )
        return response.data.value

    async def subset(
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
        request = TwoTermsRequest(
            terms=[term_subset._api_model, term_superset._api_model],
            options=self._build_options(execution_timeout),
        )
        response = await self._execute_with_retry(
            self._analyze_api.subset, two_terms_request=request
        )
        return response.data.value

    async def is_empty(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Checks if the term matches no strings at all.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the language is completely empty.
        """
        if term._empty is not None:
            return term._empty
        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.empty, term_request=request
        )
        term._empty = response.data.value
        if term._empty:
            term._cardinality = Integer(0)
            term._length = Length(min=None, max=None)
        return response.data.value

    async def is_empty_string(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Checks if the term matches only the empty string.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the term strictly matches the empty string ("") and nothing else.
        """
        if term._empty_string is not None:
            return term._empty_string
        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.empty_string, term_request=request
        )
        term._empty_string = response.data.value
        if term._empty_string:
            term._cardinality = Integer(1)
            term._length = Length(min=0, max=0)
        return response.data.value

    async def is_total(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Checks if the term matches all possible strings.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the term matches every possible strings.
        """
        if term._total is not None:
            return term._total
        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.total, term_request=request
        )
        term._total = response.data.value
        if term._total:
            term._cardinality = Infinite()
            term._length = Length(min=0, max=None)
        return response.data.value

    async def get_pattern(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> str:
        """Returns a regular expression pattern that represents the term.

        Args:
            term: The term to extract the pattern from.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            str: A valid regular expression string representing the language.
        """
        if term._pattern is not None:
            return term._pattern
        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.pattern, term_request=request
        )
        term._pattern = response.data.value
        return response.data.value

    async def get_dot(self, term: Term, execution_timeout: Optional[int] = None) -> str:
        """Builds a Graphviz DOT representation of the term's automaton.

        Args:
            term: The term to visualize.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            str: The raw DOT syntax for Graphviz compilation.
        """
        if term._dot is not None:
            return term._dot
        request = TermRequest(
            term=term._api_model, options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.dot, term_request=request
        )
        term._dot = response.data.value
        return response.data.value

    # --- COMPUTE ---
    async def concat(
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
        request = MultiTermsRequest(
            terms=[t._api_model for t in terms],
            options=self._build_options(execution_timeout, response_format),
        )
        response = await self._execute_with_retry(
            self._compute_api.concat, multi_terms_request=request
        )
        return Term(response.data)

    async def intersection(
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
        request = MultiTermsRequest(
            terms=[t._api_model for t in terms],
            options=self._build_options(execution_timeout, response_format),
        )
        response = await self._execute_with_retry(
            self._compute_api.intersection, multi_terms_request=request
        )
        return Term(response.data)

    async def union(
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
        request = MultiTermsRequest(
            terms=[t._api_model for t in terms],
            options=self._build_options(execution_timeout, response_format),
        )
        response = await self._execute_with_retry(
            self._compute_api.union, multi_terms_request=request
        )
        return Term(response.data)

    async def difference(
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
        request = TwoTermsRequest(
            terms=[base_term._api_model, excluded_term._api_model],
            options=self._build_options(execution_timeout, response_format),
        )
        response = await self._execute_with_retry(
            self._compute_api.difference, two_terms_request=request
        )
        return Term(response.data)

    async def repeat(
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
        request = RepeatRequest(
            term=term._api_model,
            min=min_val,
            max=max_val,
            options=self._build_options(execution_timeout, response_format),
        )
        response = await self._execute_with_retry(
            self._compute_api.repeat, repeat_request=request
        )
        return Term(response.data)

    # --- GENERATE ---
    async def generate_strings(
        self, term: Term, count: int, execution_timeout: Optional[int] = None
    ) -> List[str]:
        """Generates up to `count` unique strings matched by the term.

        Args:
            term: The term to sample generated strings from.
            count: The maximum number of unique strings to return.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            List[str]: A list of strings that match the term.
        """
        request = GenerateStringsRequest(
            term=term._api_model,
            count=count,
            options=self._build_options(execution_timeout),
        )
        response = await self._execute_with_retry(
            self._generate_api.strings, generate_strings_request=request
        )
        return response.data.value


class RegexSolverClient:
    """Synchronous Client for RegexSolver.

    Exposes all endpoints synchronously by managing a background event loop.
    Should be instantiated using a standard `with` context manager.
    """

    def __init__(self, api_token: str, base_url="https://api.regexsolver.com/v1"):
        self._aio = AsyncRegexSolverClient(api_token, base_url)
        # Run a background event loop so sync methods don't crash in Jupyter/FastAPI
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def _run_sync(self, coro):
        """Helper to execute async methods safely from the sync wrapper."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def close(self):
        """Closes the underlying HTTP client session and stops the background thread."""
        self._run_sync(self._aio.aclose())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()

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
        self, term: Term, count: int, execution_timeout: Optional[int] = None
    ) -> List[str]:
        """Generates up to `count` unique strings matched by the term.

        Args:
            term: The term to sample generated strings from.
            count: The maximum number of unique strings to return.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            List[str]: A list of strings that match the term.
        """
        return self._run_sync(
            self._aio.generate_strings(term, count, execution_timeout)
        )
