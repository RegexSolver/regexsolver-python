from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from regexsolver import (
    ApiError,
    Integer,
    Length,
    RegexSolverClient,
    ResponseFormat,
)
from regexsolver.generated import ApiException

# ==========================================
# FIXTURES
# ==========================================


@pytest_asyncio.fixture
def mock_term():
    """Provides a mocked Term object to avoid needing the real implementation."""
    term = MagicMock()

    # Give Pydantic a valid dictionary instead of a MagicMock!
    term._api_model = {"type": "regex", "value": "test"}

    # Initialize cache properties to None
    term._cardinality = None
    term._length = None
    term._empty = None
    term._empty_string = None
    term._total = None
    term._pattern = None
    term._dot = None

    # Mock the mixin setter so it doesn't throw errors
    term._set_properties_mixin = MagicMock()
    return term


@pytest_asyncio.fixture
async def client():
    """Provides a client with mocked underlying APIs."""
    c = RegexSolverClient(api_token="test-token")._aio

    # Mock out the generated API classes with AsyncMocks
    c._analyze_api = AsyncMock()
    c._compute_api = AsyncMock()
    c._generate_api = AsyncMock()

    yield c
    await c.aclose()


# ==========================================
# ERROR HANDLING & RATE LIMIT TESTS
# ==========================================


@pytest.mark.asyncio
async def test_429_retry_logic(client, mock_term):
    """Verifies that the client sleeps and retries on a 429 Too Many Requests."""

    # Setup the mock to fail once with 429, then succeed
    error_429 = ApiException(status=429)
    error_429.headers = {"Retry-After": "1"}

    success_response = MagicMock()
    success_response.data.value = True

    client._analyze_api.empty.side_effect = [error_429, success_response]

    # Patch asyncio.sleep so we don't actually wait during the test run
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.is_empty(mock_term)

        # Verify the 1-second sleep from the Retry-After header was called
        mock_sleep.assert_any_call(1)

        # (Optional) Verify it called sleep twice due to the mock time-freeze side-effect
        assert mock_sleep.call_count == 2

        # Verify it retried and eventually returned True
        assert result is True
        assert client._analyze_api.empty.call_count == 2


@pytest.mark.asyncio
async def test_api_error_parsing(client, mock_term):
    """Verifies that generic ApiExceptions are nicely mapped to your custom ApiError."""

    error_400 = ApiException(status=400, reason="Bad Request")
    error_400.body = '{"success": false, "error": "Invalid regex pattern"}'

    client._analyze_api.length.side_effect = error_400

    with pytest.raises(ApiError) as exc_info:
        await client.get_length(mock_term)

    assert exc_info.value.status_code == 400
    assert "Invalid regex pattern" in str(exc_info.value)


# ==========================================
# ANALYZE ENDPOINT TESTS
# ==========================================


@pytest.mark.asyncio
async def test_get_cardinality_integer(client, mock_term):
    """Tests unwrapping the generated oneOf model into your custom Integer."""

    # Simulate the messy oneOf generated payload
    mock_actual = MagicMock(type="integer", value=42)
    mock_response = MagicMock()
    mock_response.data.actual_instance = mock_actual

    client._analyze_api.cardinality.return_value = mock_response

    result = await client.get_cardinality(mock_term)

    assert isinstance(result, Integer)
    assert result.value == 42

    # Verify caching: Calling it again shouldn't trigger another network request
    await client.get_cardinality(mock_term)
    client._analyze_api.cardinality.assert_called_once()

    # Verify the mixin was updated
    mock_term._set_properties_mixin.assert_called_once_with(result)


@pytest.mark.asyncio
async def test_is_empty_string_side_effects(client, mock_term):
    """Verifies that boolean responses properly cache their sibling properties."""

    mock_response = MagicMock()
    mock_response.data.value = True
    client._analyze_api.empty_string.return_value = mock_response

    result = await client.is_empty_string(mock_term)

    assert result is True
    assert mock_term._empty_string is True

    # If it is only the empty string, it should proactively cache cardinality and length!
    assert isinstance(mock_term._cardinality, Integer)
    assert mock_term._cardinality.value == 1
    assert isinstance(mock_term._length, Length)
    assert mock_term._length.min == 0
    assert mock_term._length.max == 0


# ==========================================
# COMPUTE ENDPOINT TESTS
# ==========================================


@pytest.mark.asyncio
async def test_concat(client, mock_term):
    """Verifies multi-term requests and Enum format mappings."""

    # Because we are mocking the request object, we don't need real dictionaries anymore!
    term1 = MagicMock(_api_model="dummy_api_model_1")
    term2 = MagicMock(_api_model="dummy_api_model_2")

    mock_response = MagicMock()
    mock_response.data = "mocked_response_data"
    client._compute_api.concat.return_value = mock_response

    # Patch BOTH the custom Term class AND the generated MultiTermsRequest
    with (
        patch("regexsolver.client.Term") as MockTermClass,
        patch("regexsolver.client.MultiTermsRequest") as MockMultiTermsRequest,
    ):
        MockTermClass.return_value = "final_term_instance"

        # Tell the mock to return a dummy string instead of a strict Pydantic model
        MockMultiTermsRequest.return_value = "perfect_request_payload"

        result = await client.concat(term1, term2, response_format=ResponseFormat.REGEX)

        assert result == "final_term_instance"

        # 1. Verify we passed the exact payload to the generated API
        client._compute_api.concat.assert_called_once_with(
            multi_terms_request="perfect_request_payload"
        )

        # 2. Verify we constructed the MultiTermsRequest correctly!
        MockMultiTermsRequest.assert_called_once()
        request_kwargs = MockMultiTermsRequest.call_args.kwargs

        # Check that the raw API models were extracted and passed to the request
        assert request_kwargs["terms"] == ["dummy_api_model_1", "dummy_api_model_2"]

        # Check that the options builder successfully attached your Enum!
        assert request_kwargs["options"].response.format == ResponseFormat.REGEX


# ==========================================
# CONTEXT MANAGER TESTS
# ==========================================


@pytest.mark.asyncio
async def test_context_manager():
    """Ensures the client properly closes its session."""

    with patch("regexsolver.client.ApiClient") as MockApiClient:
        mock_instance = MockApiClient.return_value
        mock_instance.close = AsyncMock()

        async with RegexSolverClient("token")._aio as c:
            assert c is not None

        # Ensure it was safely closed upon exiting the block
        mock_instance.close.assert_called_once()
