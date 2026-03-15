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
    """Raised when the API returns a 400 Bad Request error.

    Usually indicates one of the following issues:
    - The provided regular expression is invalid or cannot be parsed.
    - The requested `execution_timeout` exceeds the maximum allowed for your current plan.
    - The number of terms provided in a multi-term operation exceeds the maximum allowed.
    - The execution of the request exceeds the provided `execution_timeout` or the maximum allowed for your current plan.
    """

    pass


class UnauthorizedError(ApiError):
    """Raised when the API returns a 401 Unauthorized error.

    Indicates that the provided authentication token is missing, malformed, or invalid.
    """

    pass


class ForbiddenError(ApiError):
    """Raised when the API returns a 403 Forbidden error.

    Usually indicates that your account's monthly compute quota has been exceeded.
    """

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
