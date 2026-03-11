from typing import Optional


class RegexSolverError(Exception):
    """Base exception for all RegexSolver errors."""

    pass


class ApiError(RegexSolverError):
    """Raised when the RegexSolver API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
