import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from regexsolver import (
    ApiError,
    AsyncRegexSolverClient,
    BadRequestError,
    ForbiddenError,
    Infinite,
    Integer,
    InvalidJsonError,
    InvalidNumberOfStringsToGenerateError,
    InvalidTokenError,
    MissingOrMalformedTokenError,
    NotFoundError,
    QuotaExceededError,
    Term,
    TimeoutExceededError,
    TimeoutTooLargeError,
    TooManyTermsError,
    UnauthorizedError,
)
from regexsolver._generated import ApiException


@pytest.fixture
async def async_client():
    client = AsyncRegexSolverClient(api_token="test-token")
    client._account_api = AsyncMock()
    client._analyze_api = AsyncMock()
    client._compute_api = AsyncMock()
    client._generate_api = AsyncMock()
    yield client
    await client.aclose()


def _term_response(value: str):
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = value
    return mock_response


def _limits_response(max_terms: int = 4):
    mock_response = MagicMock()
    mock_response.data.max_requests_count = 1000
    mock_response.data.max_requests_rate = 10
    mock_response.data.max_terms_count = max_terms
    mock_response.data.max_timeout = 60000
    mock_response.data.max_states_count = 8192
    return mock_response


def _too_many_terms_error(provided: int, allowed: int) -> ApiException:
    error = ApiException(status=400)
    error.body = (
        '{"success": false, '
        f'"error": "{provided} terms provided. Maximum allowed is {allowed}.", '
        '"errorCode": "TooManyTerms"}'
    )
    return error


@pytest.mark.asyncio
async def test_get_cardinality_integer(async_client):
    term = Term.regex("abc")

    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "integer"
    mock_response.data.actual_instance.value = 42
    async_client._analyze_api.cardinality.return_value = mock_response

    result = await async_client.get_cardinality(term)
    assert isinstance(result, Integer)
    assert result.value == 42
    assert term._cardinality == result


@pytest.mark.asyncio
async def test_get_cardinality_infinite(async_client):
    term = Term.regex(".*")

    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "infinite"
    async_client._analyze_api.cardinality.return_value = mock_response

    result = await async_client.get_cardinality(term)
    assert isinstance(result, Infinite)


@pytest.mark.asyncio
async def test_get_cardinality_big_integer(async_client):
    term = Term.regex(".{100}")

    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "bigInteger"
    async_client._analyze_api.cardinality.return_value = mock_response

    from regexsolver import BigInteger

    result = await async_client.get_cardinality(term)
    assert isinstance(result, BigInteger)


@pytest.mark.asyncio
async def test_get_length(async_client):
    term = Term.regex("abc")

    mock_response = MagicMock()
    mock_response.data.min = 3
    mock_response.data.max = 3
    async_client._analyze_api.length.return_value = mock_response

    result = await async_client.get_length(term)
    assert result.min == 3
    assert result.max == 3


@pytest.mark.asyncio
async def test_is_empty(async_client):
    term = Term.regex("[]")

    mock_response = MagicMock()
    mock_response.data.value = True
    async_client._analyze_api.empty.return_value = mock_response

    result = await async_client.is_empty(term)
    assert result is True
    assert term._empty is True


@pytest.mark.asyncio
async def test_compute_union(async_client):
    term1 = Term.regex("a")
    term2 = Term.regex("b")

    mock_response = MagicMock()
    # mock_response.data should be a GeneratedTerm
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "a|b"
    async_client._compute_api.union.return_value = mock_response

    result = await async_client.union(term1, term2)
    assert isinstance(result, Term)
    assert result.get_value() == "a|b"


@pytest.mark.asyncio
async def test_error_handling_400(async_client):
    term = Term.regex("invalid[")

    error_400 = ApiException(status=400, reason="Bad Request")
    error_400.body = '{"error": "Invalid regex"}'
    async_client._analyze_api.empty.side_effect = error_400

    with pytest.raises(BadRequestError) as exc_info:
        await async_client.is_empty(term)
    assert "Invalid regex" in str(exc_info.value)


@pytest.mark.asyncio
async def test_error_handling_invalid_json(async_client):
    error_400 = ApiException(status=400)
    error_400.body = (
        '{"success": false, "error": "Invalid JSON", "errorCode": "InvalidJson"}'
    )
    async_client._analyze_api.empty.side_effect = error_400
    with pytest.raises(InvalidJsonError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_too_many_terms(async_client):
    error_400 = ApiException(status=400)
    error_400.body = (
        '{"success": false, "error": "Too many terms", "errorCode": "TooManyTerms"}'
    )
    # Auto-batching reacts to TooManyTerms by fetching the limits; when the
    # call is already within them, the original error is re-raised.
    async_client._account_api.limits.return_value = _limits_response(max_terms=4)
    async_client._compute_api.union.side_effect = error_400
    with pytest.raises(TooManyTermsError):
        await async_client.union(Term.regex("a"), Term.regex("b"))


@pytest.mark.asyncio
async def test_error_handling_timeout_too_large(async_client):
    error_400 = ApiException(status=400)
    error_400.body = '{"success": false, "error": "Timeout too large", "errorCode": "TimeoutTooLarge"}'
    async_client._analyze_api.empty.side_effect = error_400
    with pytest.raises(TimeoutTooLargeError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_timeout_exceeded(async_client):
    error_400 = ApiException(status=400)
    error_400.body = '{"success": false, "error": "Timeout exceeded", "errorCode": "TimeoutExceeded"}'
    async_client._analyze_api.empty.side_effect = error_400
    with pytest.raises(TimeoutExceededError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_invalid_number_of_strings_to_generate(async_client):
    error_400 = ApiException(status=400)
    error_400.body = '{"success": false, "error": "Too many strings", "errorCode": "InvalidNumberOfStringsToGenerate"}'
    async_client._generate_api.strings.side_effect = error_400
    with pytest.raises(InvalidNumberOfStringsToGenerateError):
        await async_client.generate_strings(Term.regex("abc"), 100, 0)


@pytest.mark.asyncio
async def test_error_handling_missing_or_malformed_token(async_client):
    error_401 = ApiException(status=401)
    error_401.body = '{"success": false, "error": "Missing token", "errorCode": "MissingOrMalformedToken"}'
    async_client._analyze_api.empty.side_effect = error_401
    with pytest.raises(MissingOrMalformedTokenError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_invalid_token(async_client):
    error_401 = ApiException(status=401)
    error_401.body = (
        '{"success": false, "error": "Invalid token", "errorCode": "InvalidToken"}'
    )
    async_client._analyze_api.empty.side_effect = error_401
    with pytest.raises(InvalidTokenError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_quota_exceeded(async_client):
    error_403 = ApiException(status=403)
    error_403.body = (
        '{"success": false, "error": "Quota exceeded", "errorCode": "QuotaExceeded"}'
    )
    async_client._analyze_api.empty.side_effect = error_403
    with pytest.raises(QuotaExceededError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_401(async_client):
    async_client._analyze_api.empty.side_effect = ApiException(
        status=401, reason="Unauthorized"
    )

    with pytest.raises(UnauthorizedError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_403(async_client):
    async_client._analyze_api.empty.side_effect = ApiException(
        status=403, reason="Forbidden"
    )

    with pytest.raises(ForbiddenError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_404(async_client):
    async_client._analyze_api.empty.side_effect = ApiException(
        status=404, reason="Not Found"
    )

    with pytest.raises(NotFoundError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_500(async_client):
    async_client._analyze_api.empty.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )
    from regexsolver import InternalServerError

    with pytest.raises(InternalServerError):
        await async_client.is_empty(Term.regex("abc"))


@pytest.mark.asyncio
async def test_error_handling_other(async_client):
    async_client._analyze_api.empty.side_effect = ApiException(
        status=418, reason="I'm a teapot"
    )
    with pytest.raises(ApiError) as exc_info:
        await async_client.is_empty(Term.regex("abc"))
    assert exc_info.value.status_code == 418


@pytest.mark.asyncio
async def test_retry_on_429(async_client):
    term = Term.regex("abc")

    error_429 = ApiException(status=429)
    error_429.headers = {"Retry-After": "0.05"}

    success_response = MagicMock()
    success_response.data.value = True

    async_client._analyze_api.empty.side_effect = [error_429, success_response]

    result = await async_client.is_empty(term)
    assert result is True
    assert async_client._analyze_api.empty.call_count == 2


@pytest.mark.asyncio
async def test_retry_on_429_lowercase_header(async_client):
    error_429 = ApiException(status=429)
    error_429.headers = {"retry-after": "0.05"}

    success_response = MagicMock()
    success_response.data.value = True

    async_client._analyze_api.empty.side_effect = [error_429, success_response]

    assert await async_client.is_empty(Term.regex("abc")) is True
    assert async_client._analyze_api.empty.call_count == 2


@pytest.mark.asyncio
async def test_retry_survives_many_consecutive_429s(async_client):
    error_429 = ApiException(status=429)
    error_429.headers = {"Retry-After": "0.01"}

    success_response = MagicMock()
    success_response.data.value = True

    async_client._analyze_api.empty.side_effect = [error_429] * 8 + [success_response]

    with patch(
        "regexsolver.clients.asynchronous.random.uniform", return_value=0.0
    ):
        assert await async_client.is_empty(Term.regex("abc")) is True
    assert async_client._analyze_api.empty.call_count == 9


@pytest.mark.asyncio
async def test_retry_budget_exhausted():
    from regexsolver import TooManyRequestsError

    # A dedicated token: this test runs on a fake clock, which leaves the
    # shared per-token limiter with a nonsense deadline afterwards.
    client = AsyncRegexSolverClient(api_token="budget-token")
    client._analyze_api = AsyncMock()

    error_429 = ApiException(status=429)
    error_429.headers = {"Retry-After": "10"}
    client._analyze_api.empty.side_effect = error_429

    fake_now = [0.0]

    async def fake_sleep(seconds):
        fake_now[0] += seconds

    with (
        patch("time.monotonic", side_effect=lambda: fake_now[0]),
        patch("asyncio.sleep", new=fake_sleep),
        patch("regexsolver.clients.asynchronous.random.uniform", return_value=0.0),
    ):
        with pytest.raises(TooManyRequestsError) as exc_info:
            await client.is_empty(Term.regex("abc"))
    assert "Max retries exceeded" in str(exc_info.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_concurrent_429s_never_surface(async_client):
    error_429 = ApiException(status=429)
    error_429.headers = {"Retry-After": "0.02"}

    success_response = MagicMock()
    success_response.data.value = True

    async_client._analyze_api.empty.side_effect = [error_429, error_429] + [
        success_response
    ] * 7

    results = await asyncio.gather(
        *(async_client.is_empty(Term.regex("abc")) for _ in range(5))
    )
    assert results == [True] * 5


@pytest.mark.asyncio
async def test_equivalent(async_client):
    term1 = Term.regex("a")
    term2 = Term.regex("a")
    mock_response = MagicMock()
    mock_response.data.value = True
    async_client._analyze_api.equivalent.return_value = mock_response
    assert await async_client.equivalent(term1, term2) is True


@pytest.mark.asyncio
async def test_subset(async_client):
    term1 = Term.regex("a")
    term2 = Term.regex("a|b")
    mock_response = MagicMock()
    mock_response.data.value = True
    async_client._analyze_api.subset.return_value = mock_response
    assert await async_client.subset(term1, term2) is True


@pytest.mark.asyncio
async def test_is_empty_string(async_client):
    term = Term.regex("")
    mock_response = MagicMock()
    mock_response.data.value = True
    async_client._analyze_api.empty_string.return_value = mock_response
    assert await async_client.is_empty_string(term) is True


@pytest.mark.asyncio
async def test_is_total(async_client):
    term = Term.regex(".*")
    mock_response = MagicMock()
    mock_response.data.value = True
    async_client._analyze_api.total.return_value = mock_response
    assert await async_client.is_total(term) is True


@pytest.mark.asyncio
async def test_get_pattern(async_client):
    term = Term.regex("a")
    mock_response = MagicMock()
    mock_response.data.value = "a"
    async_client._analyze_api.pattern.return_value = mock_response
    assert await async_client.get_pattern(term) == "a"


@pytest.mark.asyncio
async def test_get_dot(async_client):
    term = Term.regex("a")
    mock_response = MagicMock()
    mock_response.data.value = "digraph {...}"
    async_client._analyze_api.dot.return_value = mock_response
    assert await async_client.get_dot(term) == "digraph {...}"


@pytest.mark.asyncio
async def test_concat(async_client):
    term1 = Term.regex("a")
    term2 = Term.regex("b")
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "ab"
    async_client._compute_api.concat.return_value = mock_response
    result = await async_client.concat(term1, term2)
    assert result.get_value() == "ab"


@pytest.mark.asyncio
async def test_intersection(async_client):
    term1 = Term.regex("a.")
    term2 = Term.regex(".b")
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "ab"
    async_client._compute_api.intersection.return_value = mock_response
    result = await async_client.intersection(term1, term2)
    assert result.get_value() == "ab"


@pytest.mark.asyncio
async def test_difference(async_client):
    term1 = Term.regex("a|b")
    term2 = Term.regex("b")
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "a"
    async_client._compute_api.difference.return_value = mock_response
    result = await async_client.difference(term1, term2)
    assert result.get_value() == "a"


@pytest.mark.asyncio
async def test_repeat(async_client):
    term = Term.regex("a")
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "a{2,3}"
    async_client._compute_api.repeat.return_value = mock_response
    result = await async_client.repeat(term, 2, 3)
    assert result.get_value() == "a{2,3}"


@pytest.mark.asyncio
async def test_complement(async_client):
    term = Term.regex(".*a.*")
    mock_response = MagicMock()
    mock_response.data.actual_instance.type = "regex"
    mock_response.data.actual_instance.value = "[^a].*"
    async_client._compute_api.complement.return_value = mock_response
    result = await async_client.complement(term)
    assert result.get_value() == "[^a].*"


@pytest.mark.asyncio
async def test_generate_strings(async_client):
    term = Term.regex("a*")
    mock_response = MagicMock()
    mock_response.data.strings.value = ["", "a", "aa"]
    async_client._generate_api.strings.return_value = mock_response
    result = await async_client.generate_strings(term, 3, 0)
    assert result == ["", "a", "aa"]

    request = async_client._generate_api.strings.call_args.kwargs[
        "generate_strings_request"
    ]
    # Omitted options fall back to the spec defaults baked into the model.
    assert request.path_order is None
    assert request.character_order is None
    assert request.seed == 0
    assert request.min_length == 0
    assert request.max_length == 100
    assert request.charset is None


@pytest.mark.asyncio
async def test_generate_strings_with_options(async_client):
    from regexsolver import CharacterOrder, PathOrder

    mock_response = MagicMock()
    mock_response.data.strings.value = ["xy"]
    async_client._generate_api.strings.return_value = mock_response

    result = await async_client.generate_strings(
        Term.regex("[a-z]{2}"),
        5,
        0,
        path_order=PathOrder.INTERLEAVE,
        character_order=CharacterOrder.SHUFFLED,
        seed=42,
        min_length=1,
        max_length=10,
        charset="[a-z]",
    )
    assert result == ["xy"]

    request = async_client._generate_api.strings.call_args.kwargs[
        "generate_strings_request"
    ]
    assert request.path_order == "interleave"
    assert request.character_order == "shuffled"
    assert request.seed == 42
    assert request.min_length == 1
    assert request.max_length == 10
    assert request.charset == "[a-z]"


# --- ACCOUNT LIMITS ---
@pytest.mark.asyncio
async def test_get_account_limits_memoized(async_client):
    async_client._account_api.limits.return_value = _limits_response(max_terms=4)

    limits = await async_client.get_account_limits()
    assert limits.max_requests_count == 1000
    assert limits.max_requests_rate == 10
    assert limits.max_terms_count == 4
    assert limits.max_timeout == 60000
    assert limits.max_states_count == 8192

    await async_client.get_account_limits()
    assert async_client._account_api.limits.call_count == 1


@pytest.mark.asyncio
async def test_get_account_limits_single_flight(async_client):
    async_client._account_api.limits.return_value = _limits_response()

    await asyncio.gather(
        async_client.get_account_limits(), async_client.get_account_limits()
    )
    assert async_client._account_api.limits.call_count == 1


# --- AUTO-BATCHING ---
def _request_values(call):
    request = call.kwargs["multi_terms_request"]
    return [t.actual_instance.value for t in request.terms]


@pytest.mark.asyncio
async def test_proactive_batching_with_override():
    client = AsyncRegexSolverClient(api_token="batch-token", max_terms_per_request=3)
    client._account_api = AsyncMock()
    client._compute_api = AsyncMock()
    client._compute_api.concat.side_effect = [
        _term_response(f"r{i}") for i in range(4)
    ]

    terms = [Term.regex(f"t{i}") for i in range(8)]
    result = await client.concat(*terms, response_format="regex")
    assert result.get_value() == "r3"

    calls = client._compute_api.concat.call_args_list
    assert len(calls) == 4
    # Left fold preserves concat order: contiguous chunks, accumulator first.
    assert _request_values(calls[0]) == ["t0", "t1", "t2"]
    assert _request_values(calls[1]) == ["r0", "t3", "t4"]
    assert _request_values(calls[2]) == ["r1", "t5", "t6"]
    assert _request_values(calls[3]) == ["r2", "t7"]
    # Only the final request carries the caller's response options.
    for call in calls[:3]:
        assert call.kwargs["multi_terms_request"].options.response is None
    final_options = calls[3].kwargs["multi_terms_request"].options
    assert final_options.response.format == "regex"
    # The limit was known up front, so no limits fetch happened.
    client._account_api.limits.assert_not_called()
    await client.aclose()


@pytest.mark.asyncio
async def test_reactive_batching_fetches_limits(async_client):
    async_client._account_api.limits.return_value = _limits_response(max_terms=4)
    async_client._compute_api.union.side_effect = [
        _too_many_terms_error(9, 4),
        _term_response("r0"),
        _term_response("r1"),
        _term_response("r2"),
    ]

    terms = [Term.regex(f"t{i}") for i in range(9)]
    result = await async_client.union(*terms)
    assert result.get_value() == "r2"

    calls = async_client._compute_api.union.call_args_list
    assert len(calls) == 4
    assert _request_values(calls[0]) == [f"t{i}" for i in range(9)]
    assert _request_values(calls[1]) == ["t0", "t1", "t2", "t3"]
    assert _request_values(calls[2]) == ["r0", "t4", "t5", "t6"]
    assert _request_values(calls[3]) == ["r1", "t7", "t8"]
    assert async_client._account_api.limits.call_count == 1


@pytest.mark.asyncio
async def test_batching_opt_out():
    client = AsyncRegexSolverClient(api_token="no-batch-token", auto_batch=False)
    client._account_api = AsyncMock()
    client._compute_api = AsyncMock()
    client._compute_api.union.side_effect = _too_many_terms_error(9, 4)

    terms = [Term.regex(f"t{i}") for i in range(9)]
    with pytest.raises(TooManyTermsError):
        await client.union(*terms)
    client._account_api.limits.assert_not_called()
    await client.aclose()


@pytest.mark.asyncio
async def test_batching_limits_fetch_failure_rethrows_original(async_client):
    async_client._account_api.limits.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )
    async_client._compute_api.union.side_effect = _too_many_terms_error(9, 4)

    terms = [Term.regex(f"t{i}") for i in range(9)]
    with pytest.raises(TooManyTermsError):
        await async_client.union(*terms)
    assert async_client._account_api.limits.call_count == 1


# --- CONSTRUCTOR VALIDATION ---
def test_constructor_rejects_empty_token():
    with pytest.raises(ValueError, match="api_token is required"):
        AsyncRegexSolverClient(api_token="")


def test_constructor_rejects_invalid_max_terms_per_request():
    with pytest.raises(ValueError, match="max_terms_per_request"):
        AsyncRegexSolverClient(api_token="test-token", max_terms_per_request=1)
