from unittest.mock import AsyncMock

from regexsolver import Integer, RegexSolverClient, Term


def test_sync_client_get_cardinality():
    with RegexSolverClient(api_token="test-token") as client:
        # Mock the underlying async client's method
        client._aio.get_cardinality = AsyncMock(return_value=Integer(42))

        term = Term.regex("abc")
        result = client.get_cardinality(term)

        assert isinstance(result, Integer)
        assert result.value == 42
        client._aio.get_cardinality.assert_called_once_with(term, None)


def test_sync_client_is_empty():
    with RegexSolverClient(api_token="test-token") as client:
        client._aio.is_empty = AsyncMock(return_value=False)

        term = Term.regex("abc")
        result = client.is_empty(term)

        assert result is False
        client._aio.is_empty.assert_called_once_with(term, None)


def test_sync_client_union():
    with RegexSolverClient(api_token="test-token") as client:
        mock_result_term = Term.regex("a|b")
        client._aio.union = AsyncMock(return_value=mock_result_term)

        term1 = Term.regex("a")
        term2 = Term.regex("b")
        result = client.union(term1, term2)

        assert result == mock_result_term
        client._aio.union.assert_called_once_with(
            term1, term2, response_format=None, deterministic=None, execution_timeout=None
        )


def test_sync_client_complement():
    with RegexSolverClient(api_token="test-token") as client:
        mock_result_term = Term.regex("[^a].*")
        client._aio.complement = AsyncMock(return_value=mock_result_term)

        term = Term.regex(".*a.*")
        result = client.complement(term)

        assert result == mock_result_term
        client._aio.complement.assert_called_once_with(
            term, response_format=None, deterministic=None, execution_timeout=None
        )


def test_sync_client_get_length():
    with RegexSolverClient(api_token="test-token") as client:
        from regexsolver.models.length import Length

        client._aio.get_length = AsyncMock(return_value=Length(1, 4))
        term = Term.regex("(abc)?d")
        result = client.get_length(term)
        assert result.min == 1
        assert result.max == 4


def test_sync_client_intersection():
    with RegexSolverClient(api_token="test-token") as client:
        mock_result_term = Term.regex("a")
        client._aio.intersection = AsyncMock(return_value=mock_result_term)
        t1 = Term.regex("a")
        t2 = Term.regex("ab")
        result = client.intersection(t1, t2)
        assert result == mock_result_term


def test_sync_client_generate_strings():
    with RegexSolverClient(api_token="test-token") as client:
        client._aio.generate_strings = AsyncMock(return_value=["", "a", "aa"])
        term = Term.regex("a*")
        result = client.generate_strings(term, 3, 0)
        assert result == ["", "a", "aa"]
