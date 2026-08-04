from dataclasses import dataclass

from regexsolver._generated.models import AccountLimits as GeneratedAccountLimits


@dataclass(frozen=True)
class AccountLimits:
    """The plan limits currently applying to the account.

    Attributes:
        max_requests_count (int): Maximum number of requests allowed per billing period.
        max_requests_rate (int): Maximum number of requests allowed per second. 0 means no rate limit is enforced.
        max_terms_count (int): Maximum number of terms accepted in a single request.
        max_timeout (int): Maximum execution timeout per request, in milliseconds.
        max_states_count (int): Maximum number of automaton states an operation may build.
    """

    max_requests_count: int
    max_requests_rate: int
    max_terms_count: int
    max_timeout: int
    max_states_count: int

    @classmethod
    def from_dto(cls, dto: GeneratedAccountLimits) -> "AccountLimits":
        """Converts a generated API model into a high-level AccountLimits object.

        Args:
            dto (GeneratedAccountLimits): The raw model from the generated API.

        Returns:
            AccountLimits: A high-level instance carrying the five plan limits.
        """
        return cls(
            max_requests_count=dto.max_requests_count,
            max_requests_rate=dto.max_requests_rate,
            max_terms_count=dto.max_terms_count,
            max_timeout=dto.max_timeout,
            max_states_count=dto.max_states_count,
        )

    def __repr__(self) -> str:
        return (
            f"<AccountLimits: max_requests_count={self.max_requests_count}, "
            f"max_requests_rate={self.max_requests_rate}, "
            f"max_terms_count={self.max_terms_count}, "
            f"max_timeout={self.max_timeout}, "
            f"max_states_count={self.max_states_count}>"
        )
