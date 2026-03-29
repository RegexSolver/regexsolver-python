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
    InvalidNumberOfStringsToGenerate,
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
from regexsolver.generated import ApiException


@pytest.fixture
async def async_client():
    client = AsyncRegexSolverClient(api_token="test-token")
    client._analyze_api = AsyncMock()
    client._compute_api = AsyncMock()
    client._generate_api = AsyncMock()
    yield client
    await client.aclose()


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
    with pytest.raises(InvalidNumberOfStringsToGenerate):
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
    error_429.headers = {"Retry-After": "0.1"}

    success_response = MagicMock()
    success_response.data.value = True

    async_client._analyze_api.empty.side_effect = [error_429, success_response]

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await async_client.is_empty(term)
        assert result is True
        mock_sleep.assert_called()


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
