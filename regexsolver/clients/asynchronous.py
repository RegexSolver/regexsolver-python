import asyncio
import logging
import weakref
from typing import List, Optional, Union

from regexsolver.clients.rate_limiter import get_rate_limiter
from regexsolver.exceptions import (
    ApiError,
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    InvalidJsonError,
    InvalidTokenError,
    MissingOrMalformedTokenError,
    NotFoundError,
    QuotaExceededError,
    TimeoutExceededError,
    TimeoutTooLargeError,
    TooManyRequestsError,
    TooManyStringsToGenerateError,
    TooManyTermsError,
    UnauthorizedError,
)
from regexsolver.generated import (
    AnalyzeApi,
    ApiClient,
    ApiException,
    ComputeApi,
    Configuration,
    ErrorResponse,
    ExecutionOptions,
    GenerateApi,
    GenerateStringsRequest,
    MultiTermsRequest,
    RepeatRequest,
    RequestOptions,
    ResponseOptions,
    TermRequest,
    TwoTermsRequest,
)
from regexsolver.models.cardinality import BigInteger, Infinite, Integer
from regexsolver.models.length import Length
from regexsolver.models.response_format import ResponseFormat
from regexsolver.models.term import Term

logger = logging.getLogger(__name__)


class AsyncRegexSolverClient:
    """The Asynchronous Client for RegexSolver.

    Provides non-blocking access to all RegexSolver API endpoints.
    Can be used as a standalone object or as an `async with` context manager.
    """

    def __init__(self, api_token: str, base_url="https://api.regexsolver.com/v1"):
        logger.debug("Initializing AsyncRegexSolverClient.")
        self.configuration = Configuration(host=base_url, access_token=api_token)
        self.api_client = ApiClient(self.configuration)
        self.api_client.user_agent = "RegexSolver Python / 1.1.0"

        self._analyze_api = AnalyzeApi(self.api_client)
        self._compute_api = ComputeApi(self.api_client)
        self._generate_api = GenerateApi(self.api_client)

        self._rate_limiter = get_rate_limiter(api_token)

        # Ensure the underlying aiohttp session is closed when the client is GC'd.
        self._finalizer = weakref.finalize(self, self._run_cleanup, self.api_client)

    @staticmethod
    def _run_cleanup(api_client: ApiClient):
        """Finalizer callback to safely close the async client.

        Since we cannot await in a finalizer, we try to create a task in the
        currently running loop, or just let the session be collected by aiohttp.
        """
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(api_client.close())
        except RuntimeError:
            # No loop is running, we can't do much here.
            # aiohttp will eventually emit a warning about unclosed session.
            pass

    async def aclose(self):
        """Closes the underlying HTTP client session."""
        if self._finalizer.detach():
            logger.debug("Closing AsyncRegexSolverClient.")
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
            await self._rate_limiter.wait()
            try:
                return await api_method(**kwargs)
            except ApiException as e:
                if e.status == 429:
                    retries += 1
                    if retries > max_retries:
                        logger.error("Max retries exceeded for 429 Too Many Requests.")
                        raise TooManyRequestsError(
                            "Max retries exceeded for 429 Too Many Requests.",
                            status_code=429,
                        )
                    headers = e.headers or {}
                    retry_after = float(headers.get("Retry-After", 1))
                    logger.debug(
                        f"429 Too Many Requests hit (Attempt {retries}/{max_retries}). "
                        f"Triggering rate limiter for {retry_after} seconds."
                    )
                    await self._rate_limiter.trigger(retry_after)
                    continue
                error_msg = e.reason
                error_code = None
                if e.body:
                    try:
                        parsed_error = ErrorResponse.from_json(e.body)
                        if parsed_error is not None:
                            error_msg = parsed_error.error
                            error_code = parsed_error.error_code
                        else:
                            error_msg = e.body
                    except Exception:
                        error_msg = e.body
                error_msg = str(error_msg) if error_msg else "Unknown API Error"
                error_code = str(error_code) if error_code else "UnknownError"
                logger.error(
                    f"RegexSolver API request failed with status {e.status}: {error_code}/{error_msg}"
                )

                if e.status == 400:
                    if error_code == "InvalidJson":
                        raise InvalidJsonError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    elif error_code == "TooManyTerms":
                        raise TooManyTermsError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    elif error_code == "TimeoutTooLarge":
                        raise TimeoutTooLargeError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    elif error_code == "TimeoutExceeded":
                        raise TimeoutExceededError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    elif error_code == "TooManyStringsToGenerate":
                        raise TooManyStringsToGenerateError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    raise BadRequestError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None
                elif e.status == 401:
                    if error_code == "MissingOrMalformedToken":
                        raise MissingOrMalformedTokenError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    elif error_code == "InvalidToken":
                        raise InvalidTokenError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    raise UnauthorizedError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None
                elif e.status == 403:
                    if error_code == "QuotaExceeded":
                        raise QuotaExceededError(
                            error_msg, status_code=e.status, body=e.body
                        ) from None
                    raise ForbiddenError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None
                elif e.status == 404:
                    raise NotFoundError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None
                elif e.status == 500:
                    raise InternalServerError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None
                else:
                    raise ApiError(
                        error_msg, status_code=e.status, body=e.body
                    ) from None

    def _build_options(
        self,
        execution_timeout: Optional[int] = None,
        response_format: Optional[Union[ResponseFormat, str]] = None,
    ) -> RequestOptions:
        options = RequestOptions(schemaVersion=1)
        if execution_timeout is not None:
            options.execution = ExecutionOptions(timeout=execution_timeout)
        if response_format is not None:
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
        pattern = term.get_pattern()
        if pattern is not None:
            return pattern
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
