from regexsolver.details import Details, Cardinality, Length


from typing import List, Optional
from pydantic import BaseModel
import requests

from regexsolver.details import Details


class ApiError(Exception):
    """
    Exception raised when the API returns an error.
    """

    def __init__(self, message: str):
        super().__init__(f"The API returned the following error: {message}")


class RegexSolver:
    _instance = None

    def __init__(self):
        if RegexSolver._instance is not None:
            raise Exception("This class is a singleton.")
        else:
            RegexSolver._instance = self
            self.base_url = "https://api.regexsolver.com/"
            self.api_token = None
            self.headers = {
                'User-Agent': 'RegexSolver Python / 1.0.0',
                'Content-Type': 'application/json'
            }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RegexSolver()
        return cls._instance

    @classmethod
    def initialize(cls, api_token: str, base_url: str = None):
        instance = cls.get_instance()
        instance.api_token = api_token
        if base_url:
            instance.base_url = base_url

        instance.headers['Authorization'] = f'Bearer {instance.api_token}'

    def _get_request_url(self, endpoint: str) -> str:
        if self.base_url.endswith('/'):
            return self.base_url + endpoint
        else:
            return self.base_url + '/' + endpoint

    def _request(self, endpoint: str, request: BaseModel) -> dict:
        response = requests.post(
            self._get_request_url(endpoint),
            headers=self.headers,
            json=request.model_dump()
        )

        if response.ok:
            return response.json()
        else:
            raise ApiError(response.json().get('message'))

    def compute_intersection(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/intersection', request))

    def compute_union(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/union', request))

    def compute_subtraction(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/subtraction', request))

    def get_details(self, term: 'Term') -> Details:
        return Details(**self._request('api/analyze/details', term))

    def equivalence(self, request: 'MultiTermsRequest') -> bool:
        return self._request('api/analyze/equivalence', request).get('value')

    def subset(self, request: 'MultiTermsRequest') -> bool:
        return self._request('api/analyze/subset', request).get('value')

    def generate_strings(self, request: 'GenerateStringsRequest') -> List[str]:
        return self._request('api/generate/strings', request).get('value')


_REGEX_PREFIX = "regex"
_FAIR_PREFIX = "fair"
_UNKNOWN_PREFIX = "unknown"


class Term(BaseModel):
    """
    This class represents a term on which it is possible to perform operations.
    It can either be  a regular expression (regex) or a FAIR (Fast Automaton Internal Representation).
    """

    type: str
    value: str
    _details: Optional['Details'] = None

    @classmethod
    def fair(cls, fair: str) -> 'Term':
        """
        Initialize a Fast Automaton Internal Representation (FAIR).
        """
        return cls(type=_FAIR_PREFIX, value=fair)

    @classmethod
    def regex(cls, pattern: str) -> 'Term':
        """
        Initialize a regex.
        """
        return cls(type=_REGEX_PREFIX, value=pattern)

    def get_fair(self) -> Optional[str]:
        """
        Return the Fast Automaton Internal Representation (FAIR).
        """
        if type == _FAIR_PREFIX:
            return self.value
        return None

    def get_pattern(self) -> Optional[str]:
        """
        Return the regular expression pattern.
        """
        if type == _REGEX_PREFIX:
            return self.value
        return None

    def get_details(self) -> Details:
        """
        Get the details of this term.
        Cache the result to avoid calling the API again if this method is called multiple times.
        """
        if self._details:
            return self._details
        else:
            self._details = RegexSolver.get_instance().get_details(self)
            return self._details

    def generate_strings(self, count: int) -> List[str]:
        """
        Generate the given number of unique strings matched by this term.
        """
        request = GenerateStringsRequest(term=self, count=count)
        return RegexSolver.get_instance().generate_strings(request)

    def intersection(self, *terms: 'Term') -> 'Term':
        """
        Compute the intersection with the given terms and return the resulting term.
        """
        request = MultiTermsRequest(terms=[self] + list(terms))
        return RegexSolver.get_instance().compute_intersection(request)

    def union(self, *terms: 'Term') -> 'Term':
        """
        Compute the union with the given terms and return the resulting term.
        """
        request = MultiTermsRequest(terms=[self] + list(terms))
        return RegexSolver.get_instance().compute_union(request)

    def subtraction(self, term: 'Term') -> 'Term':
        """
        Compute the subtraction with the given term and return the resulting term.
        """
        request = MultiTermsRequest(terms=[self, term])
        return RegexSolver.get_instance().compute_subtraction(request)

    def is_equivalent_to(self, term: 'Term') -> bool:
        """
        Check equivalence with the given term.
        """
        request = MultiTermsRequest(terms=[self, term])
        return RegexSolver.get_instance().equivalence(request)

    def is_subset_of(self, term: 'Term') -> bool:
        """
        Check if is a subset of the given term.
        """
        request = MultiTermsRequest(terms=[self, term])
        return RegexSolver.get_instance().subset(request)

    def serialize(self) -> str:
        """
        Generate a string representation that can be parsed by deserialize().
        """
        prefix = _UNKNOWN_PREFIX
        if self.type == _FAIR_PREFIX:
            prefix = _FAIR_PREFIX
        elif self.type == _REGEX_PREFIX:
            prefix = _REGEX_PREFIX

        return prefix + "=" + self.value

    def deserialize(string: str) -> Optional['Term']:
        """
        Parse a string representation of a Term produced by serialize().
        """
        if not string:
            return None

        if string.startswith(_REGEX_PREFIX):
            return Term.regex(string[len(_REGEX_PREFIX)+1:])
        elif string.startswith(_FAIR_PREFIX):
            return Term.fair(string[len(_FAIR_PREFIX)+1:])
        else:
            return None

    def __str__(self):
        return self.serialize()

    def __eq__(self, other):
        if isinstance(other, Term):
            return self.type == other.type and self.value == other.value
        return False

    def __hash__(self):
        return hash(self.serialize())


class MultiTermsRequest(BaseModel):
    terms: List[Term]


class GenerateStringsRequest(BaseModel):
    term: Term
    count: int
