import asyncio
import logging
import random
import time
import weakref
from typing import Awaitable, Callable, List, Optional, Union

from pydantic import ValidationError

from regexsolver._generated import (
    AccountApi,
    AnalyzeApi,
    ApiClient,
    ApiException,
    ComputeApi,
    Configuration,
    ErrorResponse,
    ExecutionOptions,
    FairResponseOptions,
    GenerateApi,
    GenerateStringsRequest,
    MultiTermsRequest,
    RepeatRequest,
    RequestOptions,
    ResponseOptions,
    TermRequest,
    TwoTermsRequest,
)
from regexsolver.clients.rate_limiter import get_rate_limiter
from regexsolver.exceptions import (
    ApiError,
    AutomatonTooManyStatesError,
    BadRequestError,
    FairSyntaxError,
    ForbiddenError,
    InternalServerError,
    InvalidJsonError,
    InvalidNumberOfStringsToGenerateError,
    InvalidTokenError,
    MissingOrMalformedTokenError,
    NotFoundError,
    QuotaExceededError,
    RegexSolverError,
    RegexSyntaxError,
    TimeoutExceededError,
    TimeoutTooLargeError,
    TooFewTermsError,
    TooManyRequestsError,
    TooManyTermsError,
    UnauthorizedError,
)
from regexsolver.models.account_limits import AccountLimits
from regexsolver.models.cardinality import Cardinality, Infinite, Integer
from regexsolver.models.generate_order import CharacterOrder, PathOrder
from regexsolver.models.length import Length
from regexsolver.models.response_format import ResponseFormat
from regexsolver.models.term import FairTerm, Term

logger = logging.getLogger(__name__)

# Retry policy for 429 responses: retry as long as the total wait stays
# within the budget, adding full jitter on top of `Retry-After` so concurrent
# waiters do not re-collide as a single burst. The values are shared across
# all the official clients — change them together.
_RETRY_BUDGET_S = 300.0
_JITTER_BASE_S = 0.25
_JITTER_CAP_S = 2.0
_DEFAULT_RETRY_AFTER_S = 1.0


def _get_retry_after(headers) -> float:
    """Case-insensitively read the Retry-After header, in seconds."""
    for key, value in (headers or {}).items():
        if str(key).lower() == "retry-after":
            try:
                return float(value)
            except (TypeError, ValueError):
                break
    return _DEFAULT_RETRY_AFTER_S


def _build_request(model, **kwargs):
    """Build a generated request model, keeping pydantic out of the public surface.

    The generated models carry the constraints declared in openapi.yaml (`terms`
    minItems, `limit` range), so an invalid call is rejected before it is sent --
    which is good, it saves a round trip. But the raw `pydantic.ValidationError`
    is not a `RegexSolverError`, so callers writing `except RegexSolverError`
    would miss it. Translate it into the same error the API would have returned.
    """
    try:
        return model(**kwargs)
    except ValidationError as e:
        raise _map_validation_error(e) from e


def _map_validation_error(e: ValidationError) -> RegexSolverError:
    errors = e.errors()
    fields = {str(err["loc"][0]) for err in errors if err.get("loc")}
    message = "; ".join(
        f"{'.'.join(str(part) for part in err.get('loc', ()))}: {err['msg']}"
        for err in errors
    )

    if "terms" in fields:
        return TooFewTermsError(message, status_code=400)
    if fields & {"limit", "offset"}:
        return InvalidNumberOfStringsToGenerateError(message, status_code=400)
    return BadRequestError(message, status_code=400)


class AsyncRegexSolverClient:
    """The Asynchronous Client for RegexSolver.

    Provides non-blocking access to all RegexSolver API endpoints.
    Can be used as a standalone object or as an `async with` context manager.
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://api.regexsolver.com/v1",
        auto_batch: bool = True,
        max_terms_per_request: Optional[int] = None,
    ):
        if not api_token:
            raise ValueError("api_token is required")
        if max_terms_per_request is not None and max_terms_per_request < 2:
            raise ValueError("max_terms_per_request must be at least 2")

        logger.debug("Initializing AsyncRegexSolverClient.")
        self.configuration = Configuration(host=base_url, access_token=api_token)
        self.api_client = ApiClient(self.configuration)
        self.api_client.user_agent = "RegexSolver Python / 1.1.0"

        self._account_api = AccountApi(self.api_client)
        self._analyze_api = AnalyzeApi(self.api_client)
        self._compute_api = ComputeApi(self.api_client)
        self._generate_api = GenerateApi(self.api_client)

        self._rate_limiter = get_rate_limiter(api_token)

        self._auto_batch = auto_batch
        self._max_terms_per_request = max_terms_per_request
        self._limits: Optional[AccountLimits] = None
        # Created lazily: asyncio primitives must be born on the running loop.
        self._limits_lock: Optional[asyncio.Lock] = None

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
        attempt = 0
        first_failure_at: Optional[float] = None
        while True:
            await self._rate_limiter.wait()
            if attempt > 0:
                await asyncio.sleep(
                    random.uniform(0.0, min(_JITTER_BASE_S * 2**attempt, _JITTER_CAP_S))
                )
            try:
                return await api_method(**kwargs)
            except ApiException as e:
                if e.status != 429:
                    raise self._map_error(e)

                retry_after = _get_retry_after(e.headers)
                now = time.monotonic()
                if first_failure_at is None:
                    first_failure_at = now
                if now - first_failure_at + retry_after > _RETRY_BUDGET_S:
                    raise self._map_error(e)

                logger.debug(
                    "429 Too Many Requests hit. "
                    f"Triggering rate limiter for {retry_after} seconds."
                )
                self._rate_limiter.trigger(retry_after)
                attempt += 1

    def _map_error(self, e: ApiException) -> Exception:
        status_code = e.status
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
            f"RegexSolver API request failed with status {status_code}: {error_code}/{error_msg}"
        )

        if status_code == 400:
            if error_code == "InvalidJson":
                return InvalidJsonError(error_msg, status_code=status_code, body=e.body)
            if error_code == "TooManyTerms":
                return TooManyTermsError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "TooFewTerms":
                return TooFewTermsError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "TimeoutTooLarge":
                return TimeoutTooLargeError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "TimeoutExceeded":
                return TimeoutExceededError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "InvalidNumberOfStringsToGenerate":
                return InvalidNumberOfStringsToGenerateError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "AutomatonTooManyStates":
                return AutomatonTooManyStatesError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "RegexSyntaxError":
                return RegexSyntaxError(error_msg, status_code=status_code, body=e.body)
            if error_code == "FairSyntaxError":
                return FairSyntaxError(error_msg, status_code=status_code, body=e.body)
            return BadRequestError(error_msg, status_code=status_code, body=e.body)

        elif status_code == 401:
            if error_code == "MissingOrMalformedToken":
                return MissingOrMalformedTokenError(
                    error_msg, status_code=status_code, body=e.body
                )
            if error_code == "InvalidToken":
                return InvalidTokenError(
                    error_msg, status_code=status_code, body=e.body
                )
            return UnauthorizedError(error_msg, status_code=status_code, body=e.body)

        elif status_code == 403:
            if error_code == "QuotaExceeded":
                return QuotaExceededError(
                    error_msg, status_code=status_code, body=e.body
                )
            return ForbiddenError(error_msg, status_code=status_code, body=e.body)

        elif status_code == 404:
            return NotFoundError(error_msg, status_code=status_code, body=e.body)

        elif status_code == 429:
            msg = (
                "Max retries exceeded for 429 Too Many Requests."
                if error_msg == "Unknown API Error"
                else error_msg
            )
            return TooManyRequestsError(msg, status_code=429)

        elif status_code == 500:
            return InternalServerError(error_msg, status_code=status_code, body=e.body)

        else:
            return ApiError(error_msg, status_code=status_code, body=e.body)

    def _build_options(
        self,
        execution_timeout: Optional[int] = None,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
    ) -> RequestOptions:
        if deterministic is not None and response_format is not None:
            fmt = (
                ResponseFormat(response_format)
                if isinstance(response_format, str)
                else response_format
            )
            if fmt != ResponseFormat.FAIR:
                raise ValueError(
                    f"deterministic can only be used with response_format=ResponseFormat.FAIR, got {fmt!r}"
                )
        options = RequestOptions(schemaVersion=1)
        if execution_timeout is not None:
            options.execution = ExecutionOptions(timeout=execution_timeout)
        response_opts = ResponseOptions()
        if response_format is not None:
            response_opts.format = str(response_format)
        if deterministic is not None:
            response_opts.fair = FairResponseOptions(deterministic=deterministic)
            if response_format is None:
                # FairResponseOptions is only applied when the response format is
                # "fair", so default to it to honor the deterministic request.
                response_opts.format = str(ResponseFormat.FAIR)
        if response_format is not None or deterministic is not None:
            options.response = response_opts
        return options

    # --- ACCOUNT ---
    async def get_account_limits(self) -> AccountLimits:
        """Fetches the plan limits applying to the account.

        The call never consumes request quota (it is only rate-limited) and
        the result is cached on the client, so calling it again is free. The
        cached `max_terms_count` also drives auto-batching.

        Returns:
            AccountLimits: The five plan limits.
        """
        if self._limits is not None:
            return self._limits
        if self._limits_lock is None:
            self._limits_lock = asyncio.Lock()
        async with self._limits_lock:
            if self._limits is None:
                response = await self._execute_with_retry(self._account_api.limits)
                self._limits = AccountLimits.from_dto(response.data)
        return self._limits

    # --- BATCHING ---
    def _effective_max_terms(self) -> Optional[int]:
        """The largest term count to send in one request, when known."""
        server_max = self._limits.max_terms_count if self._limits else None
        if self._max_terms_per_request is not None:
            if server_max is not None:
                return min(self._max_terms_per_request, server_max)
            return self._max_terms_per_request
        return server_max

    async def _run_nary(
        self,
        api_method,
        terms,
        response_format: Optional[Union[ResponseFormat, str]],
        deterministic: Optional[bool],
        execution_timeout: Optional[int],
    ) -> Term:
        """Run an n-ary operation (concat/intersection/union), transparently
        splitting the terms into several requests when they exceed the
        account's terms-per-request limit (auto-batching).
        """
        terms = list(terms)

        async def call(batch: List[Term], final: bool) -> Term:
            # Intermediate results are fed straight back into the next
            # request, so only the final call carries the caller's response
            # options; execution_timeout bounds every constituent request.
            request = _build_request(
                MultiTermsRequest,
                terms=[t.to_dto() for t in batch],
                options=self._build_options(
                    execution_timeout,
                    response_format if final else None,
                    deterministic if final else None,
                ),
            )
            response = await self._execute_with_retry(
                api_method, multi_terms_request=request
            )
            return Term.from_dto(response.data)

        max_terms = self._effective_max_terms() if self._auto_batch else None
        if max_terms is not None and len(terms) > max_terms:
            return await self._fold(call, terms, max_terms)

        try:
            return await call(terms, True)
        except TooManyTermsError as too_many:
            if not self._auto_batch or max_terms is not None:
                raise
            try:
                await self.get_account_limits()
            except RegexSolverError as fetch_error:
                logger.debug(f"Fetching account limits failed: {fetch_error}")
                raise too_many from None
            max_terms = self._effective_max_terms()
            if max_terms is None or max_terms < 2 or len(terms) <= max_terms:
                raise
            return await self._fold(call, terms, max_terms)

    @staticmethod
    async def _fold(
        call: Callable[[List[Term], bool], Awaitable[Term]],
        terms: List[Term],
        max_terms: int,
    ) -> Term:
        """Left fold: combine the first `max_terms` terms, then keep feeding
        the accumulated result back with the next `max_terms - 1` terms.
        Left-associative, so `concat` order is preserved; `union` and
        `intersection` are commutative and unaffected.
        """
        acc = await call(terms[:max_terms], False)
        index = max_terms
        while index < len(terms):
            batch = [acc] + terms[index: index + max_terms - 1]
            index += max_terms - 1
            acc = await call(batch, index >= len(terms))
        return acc

    # --- ANALYZE ---
    async def get_cardinality(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> Cardinality:
        """Computes how many unique strings the term matches.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Cardinality: An object representing either an exact Integer, a BigInteger, or Infinite cardinality.
        """
        if term._cardinality is not None:
            return term._cardinality

        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.cardinality, term_request=request
        )

        term._cardinality = Cardinality.from_dto(response.data)
        term._set_properties_mixin(term._cardinality)
        return term._cardinality

    async def get_length(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> Length:
        """Computes the minimum and maximum length of strings matched by the term.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Length: An object containing `min` and `max` integers. Limits are `None` if unbounded or undefined.
        """
        if term._length is not None:
            return term._length

        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.length, term_request=request
        )

        term._length = Length.from_dto(response.data)
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
        request = _build_request(
            TwoTermsRequest,
            terms=[term1.to_dto(), term2.to_dto()],
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
        request = _build_request(
            TwoTermsRequest,
            terms=[term_subset.to_dto(), term_superset.to_dto()],
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
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
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
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
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
            bool: True if the term matches every possible string.
        """
        if term._total is not None:
            return term._total
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.total, term_request=request
        )
        term._total = response.data.value
        if term._total:
            term._cardinality = Infinite()
            term._length = Length(min=0, max=None)
        return response.data.value

    async def is_deterministic(
        self, term: Term, execution_timeout: Optional[int] = None
    ) -> bool:
        """Check if the term's automaton is deterministic.
        Only a deterministic FAIR guarantees consistent string ordering across
        paginated generate_strings requests; call determinize first if this is false.

        Args:
            term: The term to analyze.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            bool: True if the term's automaton is deterministic.
        """
        if not isinstance(term, FairTerm):
            return False

        if term._deterministic is not None:
            return term._deterministic
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
        )
        response = await self._execute_with_retry(
            self._analyze_api.deterministic, term_request=request
        )
        term._deterministic = response.data.value
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
        pattern = term._pattern
        if pattern is not None:
            return pattern
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
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
        request = _build_request(
            TermRequest,
            term=term.to_dto(), options=self._build_options(execution_timeout)
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
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Concatenates the given terms sequentially.

        Args:
            *terms: A dynamic list of terms to concatenate in order.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A newly computed concatenated term.
        """
        return await self._run_nary(
            self._compute_api.concat,
            terms,
            response_format,
            deterministic,
            execution_timeout,
        )

    async def intersection(
        self,
        *terms: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the intersection of the given terms.

        Args:
            *terms: A dynamic list of terms to intersect.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A term representing only strings matched by ALL provided terms.
        """
        return await self._run_nary(
            self._compute_api.intersection,
            terms,
            response_format,
            deterministic,
            execution_timeout,
        )

    async def union(
        self,
        *terms: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the union of the given terms.

        Args:
            *terms: A dynamic list of terms to combine.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A term representing strings matched by ANY of the provided terms.
        """
        return await self._run_nary(
            self._compute_api.union,
            terms,
            response_format,
            deterministic,
            execution_timeout,
        )

    async def difference(
        self,
        base_term: Term,
        excluded_term: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the difference between the two given terms.

        Args:
            base_term: The base language term to subtract from.
            excluded_term: The term whose language should be removed from the base.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A computed difference term.
        """
        request = _build_request(
            TwoTermsRequest,
            terms=[base_term.to_dto(), excluded_term.to_dto()],
            options=self._build_options(
                execution_timeout, response_format, deterministic
            ),
        )
        response = await self._execute_with_retry(
            self._compute_api.difference, two_terms_request=request
        )
        return Term.from_dto(response.data)

    async def repeat(
        self,
        term: Term,
        min_val: int,
        max_val: Optional[int] = None,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Repeats a term between a minimum and maximum number of times.

        Args:
            term: The term to repeat.
            min_val: The inclusive lower bound of repetitions.
            max_val: The inclusive upper bound. If None, repetitions are unbounded.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A computed repeated term.
        """
        request = _build_request(
            RepeatRequest,
            term=term.to_dto(),
            min=min_val,
            max=max_val,
            options=self._build_options(
                execution_timeout, response_format, deterministic
            ),
        )
        response = await self._execute_with_retry(
            self._compute_api.repeat, repeat_request=request
        )
        return Term.from_dto(response.data)

    async def complement(
        self,
        term: Term,
        response_format: Optional[Union[ResponseFormat, str]] = None,
        deterministic: Optional[bool] = None,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes the complement of the given term.

        Args:
            term: The term to complement.
            response_format: The return format of the term (any, regex or fair).
            deterministic: When True, guarantees the returned FAIR encodes a deterministic
                automaton. Only valid with response_format=ResponseFormat.FAIR or when
                response_format is unset. Raises ValueError otherwise.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: The complemented term.
        """
        request = _build_request(
            TermRequest,
            term=term.to_dto(),
            options=self._build_options(
                execution_timeout, response_format, deterministic
            ),
        )
        response = await self._execute_with_retry(
            self._compute_api.complement, term_request=request
        )
        return Term.from_dto(response.data)

    async def determinize(
        self,
        term: Term,
        execution_timeout: Optional[int] = None,
    ) -> Term:
        """Computes a deterministic FAIR automaton from the given term.

        A deterministic FAIR guarantees consistent string ordering across paginated
        generate_strings requests. Use this when term.is_deterministic is False or None
        before calling generate_strings with an offset.

        Args:
            term: The term to determinize.
            execution_timeout: Timeout in milliseconds for the operation.

        Returns:
            Term: A deterministic FAIR.
        """
        request = _build_request(
            TermRequest,
            term=term.to_dto(),
            options=self._build_options(execution_timeout),
        )
        response = await self._execute_with_retry(
            self._compute_api.determinize, term_request=request
        )
        return Term.from_dto(response.data)

    # --- GENERATE ---
    async def generate_strings(
        self,
        term: Term,
        limit: int,
        offset: int,
        execution_timeout: Optional[int] = None,
        *,
        path_order: Optional[Union[PathOrder, str]] = None,
        character_order: Optional[Union[CharacterOrder, str]] = None,
        seed: Optional[int] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        charset: Optional[str] = None,
    ) -> List[str]:
        """Generates up to `limit` distinct strings matched by `term`, skipping the first `offset` strings.

        Args:
            term: The term to sample generated strings from.
            limit: The maximum number of unique strings to return.
            offset: Number of matched strings to skip before starting to collect the results. Used for pagination.
            execution_timeout: Timeout in milliseconds for the operation.
            path_order: Order in which the paths (shapes) of the language are
                scheduled (sweep, interleave or shuffled). Defaults to sweep.
            character_order: Order in which the strings within each path are
                produced (ascending or shuffled). Defaults to ascending.
            seed: Seed behind the shuffled modes. The default seed is fixed,
                so two calls sharing a seed generate the same strings and
                `offset` pages through them consistently.
            min_length: Shortest string to generate. Shorter strings are left
                out of the enumeration entirely, `offset` never counting them.
            max_length: Longest string to generate.
            charset: Restricts generation to the given characters, e.g.
                `[a-z]`. Paths requiring a character outside it are dropped.

        Returns:
            List[str]: A list of strings that match the term.
        """
        kwargs = dict(
            term=term.to_dto(),
            limit=limit,
            offset=offset,
            options=self._build_options(execution_timeout),
        )
        if path_order is not None:
            kwargs["path_order"] = str(path_order)
        if character_order is not None:
            kwargs["character_order"] = str(character_order)
        if seed is not None:
            kwargs["seed"] = seed
        if min_length is not None:
            kwargs["min_length"] = min_length
        if max_length is not None:
            kwargs["max_length"] = max_length
        if charset is not None:
            kwargs["charset"] = charset

        request = _build_request(GenerateStringsRequest, **kwargs)
        response = await self._execute_with_retry(
            self._generate_api.strings, generate_strings_request=request
        )

        return response.data.strings.value
