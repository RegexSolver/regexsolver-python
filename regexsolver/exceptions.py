from typing import Optional


class RegexSolverError(Exception):
    """Base exception for all RegexSolver errors."""

    pass


class ApiError(RegexSolverError):
    """Base exception raised when the RegexSolver API returns an error response.

    Attributes:
        status_code (Optional[int]): The HTTP status code returned by the API.
        body (Optional[str]): The raw string body of the error response.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class BadRequestError(ApiError):
    """Raised when the API returns a 400 Bad Request error."""

    pass


class InvalidJsonError(BadRequestError):
    """Raised when the provided JSON is invalid or cannot be parsed."""

    pass


class TooManyTermsError(BadRequestError):
    """Raised when the number of terms provided exceeds the maximum allowed."""

    pass


class TimeoutTooLargeError(BadRequestError):
    """Raised when the requested `execution_timeout` exceeds the maximum allowed for your current plan."""

    pass


class TimeoutExceededError(BadRequestError):
    """Raised when the execution of the request exceeds the provided `execution_timeout` or the maximum allowed for your current plan."""

    pass


class InvalidNumberOfStringsToGenerate(BadRequestError):
    """Raised when the requested number of strings to generate is below the minimum or exceeds the maximum allowed."""

    pass


class UnauthorizedError(ApiError):
    """Raised when the API returns a 401 Unauthorized error."""

    pass


class MissingOrMalformedTokenError(UnauthorizedError):
    """Raised when the provided authentication token is missing or malformed."""

    pass


class InvalidTokenError(UnauthorizedError):
    """Raised when the provided authentication token is invalid."""

    pass


class ForbiddenError(ApiError):
    """Raised when the API returns a 403 Forbidden error."""

    pass


class QuotaExceededError(ForbiddenError):
    """Raised when your account's monthly compute quota has been exceeded."""

    pass


class NotFoundError(ApiError):
    """Raised when the API returns a 404 Not Found error.

    Indicates that the requested API endpoint or resource does not exist.
    """

    pass


class TooManyRequestsError(ApiError):
    """Raised when the API returns a 429 Too Many Requests error and max retries are exceeded.

    Indicates that your requests-per-second (req/s) rate limit has been exceeded.
    """

    pass


class InternalServerError(ApiError):
    """Raised when the API returns a 500 Internal Server Error.

    Indicates an unexpected failure or panic on the RegexSolver compute servers.
    """

    pass
