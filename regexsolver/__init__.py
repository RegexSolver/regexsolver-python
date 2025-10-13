from enum import Enum
from importlib import metadata
import os
from regexsolver.details import Details, Cardinality, Length


from typing import List, Optional
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

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
            
            load_dotenv()
            
            self._base_url = os.environ.get("REGEXSOLVER_BASE_URL", "https://api.regexsolver.com")
            self._api_token = os.environ.get("REGEXSOLVER_API_TOKEN") or None
            
            self._headers = {
                'User-Agent': 'RegexSolver Python / 1.1.0',
                'Content-Type': 'application/json'
            }
            if self._api_token:
                self._headers['Authorization'] = f'Bearer {self._api_token}'

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = RegexSolver()
        return cls._instance

    @classmethod
    def initialize(cls, api_token: str, base_url: str = None):
        instance = cls.get_instance()
        instance._api_token = api_token
        if base_url:
            instance._base_url = base_url

        instance._headers['Authorization'] = f'Bearer {instance._api_token}'

    def _get_request_url(self, endpoint: str) -> str:
        if self._base_url.endswith('/'):
            return self._base_url + endpoint
        else:
            return self._base_url + '/' + endpoint

    def _request(self, endpoint: str, request: BaseModel) -> dict:
        response = requests.post(
            self._get_request_url(endpoint),
            headers=self._headers,
            json=request.model_dump(exclude_none=True)
        )

        if response.ok:
            return response.json()
        try:
            data = response.json()
            msg = data.get("message", response.text)
        except Exception:
            msg = response.text
        raise ApiError(msg)
    
    # Analyze
    
    def _analyze_details(self, term: 'Term') -> Details:
        return Details(**self._request('api/analyze/details', term))
    
    def _analyze_cardinality(self, term: 'Term') -> Cardinality:
        return Cardinality(**self._request('api/analyze/cardinality', term))
    
    def _analyze_length(self, term: 'Term') -> Length:
        return Length(**self._request('api/analyze/length', term))
    
    def _analyze_equivalent(self, request: 'MultiTermsRequest') -> bool:
        return self._request('api/analyze/equivalent', request).get('value')

    def _analyze_subset(self, request: 'MultiTermsRequest') -> bool:
        return self._request('api/analyze/subset', request).get('value')
    
    def _analyze_empty(self, term: 'Term') -> bool:
        return self._request('api/analyze/empty', term).get('value')
    
    def _analyze_total(self, term: 'Term') -> bool:
        return self._request('api/analyze/total', term).get('value')
    
    def _analyze_empty_string(self, term: 'Term') -> bool:
        return self._request('api/analyze/empty_string', term).get('value')
        
    def _analyze_dot(self, term: 'Term') -> str:
        return self._request('api/analyze/dot', term).get('value')
    
    def _analyze_pattern(self, term: 'Term') -> str:
        return self._request('api/analyze/pattern', term).get('value')
    
    # Compute
    
    def _compute_repeat(self, request: 'RepeatRequest') -> 'Term':
        return Term(**self._request('api/compute/repeat', request))

    def _compute_intersection(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/intersection', request))

    def _compute_union(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/union', request))

    def _compute_difference(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/difference', request))
    
    def _compute_concat(self, request: 'MultiTermsRequest') -> 'Term':
        return Term(**self._request('api/compute/concat', request))
    
    # Generate

    def _generate_strings(self, request: 'GenerateStringsRequest') -> List[str]:
        return self._request('api/generate/strings', request).get('value')
    
    
class TermType(str, Enum):
    FAIR = "fair"
    REGEX = "regex"


class Term(BaseModel):
    """
    Represents a term on which operations can be performed.
    A term can be either:
    - A regular expression (`regex`)
    - A FAIR (Fast Automaton Internal Representation, `fair`)

    Convenience constructors:
    - `Term.regex(pattern: str)`
    - `Term.fair(fair: str)`
    """

    type: TermType
    value: str
    _details: Optional['Details'] = None
    _cardinality: Optional[Cardinality] = None
    _length: Optional[Length] = None
    _empty: Optional[bool] = None
    _total: Optional[bool] = None
    _empty_string: Optional[bool] = None
    _dot: Optional[str] = None
    _pattern: Optional[str] = None
    
    model_config = {"use_enum_values": True}

    @classmethod
    def fair(cls, fair: str) -> 'Term':
        """
        Initialize a Fast Automaton Internal Representation (FAIR).
        """
        return cls(type=TermType.FAIR, value=fair)

    @classmethod
    def regex(cls, pattern: str) -> 'Term':
        """
        Initialize a regex.
        """
        return cls(type=TermType.REGEX, value=pattern)

    def get_fair(self) -> Optional[str]:
        """
        Return the Fast Automaton Internal Representation (FAIR).
        """
        if self.type == TermType.FAIR:
            return self.value
        return None

    def get_pattern(self) -> Optional[str]:
        """
        Return the regular expression pattern.
        
        If the term is not a regex the pattern will be resolved.
        Results are cached on the instance to avoid repeated API calls.
        """
        if self.type == TermType.REGEX:
            return self.value
        elif self._pattern:
            return self._pattern
        else:
            self._pattern = RegexSolver.get_instance()._analyze_pattern(self)
            return self._pattern

    def get_details(self) -> Details:
        """
        Analyze this term and return detailed information including cardinality,
        length, and whether it is empty or total.

        Results are cached on the instance to avoid repeated API calls.
        """
        if self._details:
            return self._details
        else:
            self._details = RegexSolver.get_instance()._analyze_details(self)
            return self._details

    def generate_strings(self, count: int, execution_timeout=None) -> List[str]:
        """
        Generate up to `count` example strings that match this term.

        Parameters:
            count: Maximum number of unique strings to generate.
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            A list of strings matched by this term.
        """
        request = GenerateStringsRequest(term=self, count=count, options=RequestOptions.from_args(execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._generate_strings(request)

    def intersection(self, *terms: 'Term', response_format=None, execution_timeout=None) -> 'Term':
        """
        Compute the intersection of this term with one or more other terms.

        Parameters:
            terms: Additional terms to intersect with.
            response_format: Output format (`regex`, `fair`, or `any`).
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            A new term representing the intersection.
        """
        request = MultiTermsRequest(terms=[self] + list(terms), options=RequestOptions.from_args(response_format=response_format, execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._compute_intersection(request)

    def union(self, *terms: 'Term', response_format=None, execution_timeout=None) -> 'Term':
        """
        Compute the union of this term with one or more other terms.

        Parameters:
            terms: Terms to combine with this one.
            response_format: Output format (`regex`, `fair`, or `any`).
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            A new term representing the union.
        """
        request = MultiTermsRequest(terms=[self] + list(terms), options=RequestOptions.from_args(response_format=response_format, execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._compute_union(request)

    def difference(self, term: 'Term', response_format=None, execution_timeout=None) -> 'Term':
        """
        Compute the difference between this term and another.

        Parameters:
            term: The term to subtract from this one.
            response_format: Output format (`regex`, `fair`, or `any`).
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            A new term representing the set difference (this - term).
        """
        request = MultiTermsRequest(terms=[self, term], options=RequestOptions.from_args(response_format=response_format, execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._compute_difference(request)
    
    def concat(self, *terms: 'Term', response_format=None, execution_timeout=None) -> 'Term':
        """
        Concatenate this term with one or more other terms.

        Parameters:
            terms: Additional terms to append in sequence.
            response_format: Output format (`regex`, `fair`, or `any`).
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            A new term representing the concatenation.
        """
        request = MultiTermsRequest(terms=[self] + list(terms), options=RequestOptions.from_args(response_format=response_format, execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._compute_concat(request)
    
    def equivalent(self, term: 'Term', execution_timeout=None) -> bool:
        """
        Check whether this term is equivalent to another.

        Parameters:
            term: The term to compare against.
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            True if both terms accept exactly the same language.
        """
        request = MultiTermsRequest(terms=[self, term], options=RequestOptions.from_args(execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._analyze_equivalent(request)
    
    def subset(self, term: 'Term', execution_timeout=None) -> bool:
        """
        Check whether this term is a subset of another.

        Parameters:
            term: The term to compare against.
            execution_timeout: Timeout in milliseconds for the server.

        Returns:
            True if every string matched by this term is also matched by `term`.
        """
        request = MultiTermsRequest(terms=[self, term], options=RequestOptions.from_args(execution_timeout=execution_timeout))
        return RegexSolver.get_instance()._analyze_subset(request)
    
    def is_empty(self) -> bool:
        """
        Check whether this term matches no string.

        Results are cached on the instance to avoid repeated API calls.
        """
        if self._empty:
            return self._empty
        elif self._details:
            return self._details.empty
        else:
            self._empty = RegexSolver.get_instance()._analyze_empty(self)
            return self._empty
        
    def is_total(self) -> bool:
        """
        Check whether this term matches all possible strings.

        Results are cached on the instance to avoid repeated API calls.
        """
        if self._total:
            return self._total
        elif self._details:
            return self._details.total
        else:
            self._total = RegexSolver.get_instance()._analyze_total(self)
            return self._total
        
    def is_empty_string(self) -> bool:
        """
        Check whether this term matches only the empty string.

        Results are cached on the instance to avoid repeated API calls.
        """
        if self._empty_string:
            return self._empty_string
        else:
            self._empty_string = RegexSolver.get_instance()._analyze_empty_string(self)
            return self._empty_string
        
    def get_dot(self) -> str:
        """
        Get the GraphViz DOT representation of this term.
        
        Results are cached on the instance to avoid repeated API calls.

        Returns:
            A DOT language string describing the automaton for this term.
        """
        if self._dot:
            return self._dot
        else:
            self._dot = RegexSolver.get_instance()._analyze_dot(self)
            return self._dot
    
    def get_cardinality(self) -> Cardinality:
        """
        Get the cardinality of this term.
        
        Results are cached on the instance to avoid repeated API calls.

        Returns:
            A `Cardinality` object describing how many distinct strings
            are matched.
        """
        
        if self._cardinality:
            return self._cardinality
        elif self._details:
            return self._details.cardinality
        else:
            self._cardinality = RegexSolver.get_instance()._analyze_cardinality(self)
            return self._cardinality
    
    def get_length(self) -> Length:
        """
        Get the length bounds of this term.
        
        Results are cached on the instance to avoid repeated API calls.

        Returns:
            A `Length` object with the minimum and maximum string length
            matched by this term.
        """
        if self._length:
            return self._length
        elif self._length:
            return self._details.length
        else:
            self._length = RegexSolver.get_instance()._analyze_length(self)
            return self._length

    def serialize(self) -> str:
        """
        Return a string representation of this term in the format
        `<type>=<value>`, which can later be parsed by `deserialize()`.
        """
        if self.type == TermType.FAIR:
            prefix = TermType.FAIR
        elif self.type == TermType.REGEX:
            prefix = TermType.REGEX
        else:
            raise ValueError(f"Unknown type: {self.type}")
    
        return prefix + "=" + self.value

    @staticmethod
    def deserialize(string: str) -> Optional['Term']:
        """
        Parse a string representation produced by `serialize()`.

        Parameters:
            string: The serialized term, e.g. `"regex=abc"`.

        Returns:
            A Term instance, or None if the input is empty or invalid.
        """
        if not string or "=" not in string:
            return None
        prefix, value = string.split("=", 1)
        if prefix == TermType.REGEX:
            return Term.regex(value)
        elif prefix == TermType.FAIR:
            return Term.fair(value)
        return None

    def __str__(self):
        return self.serialize()

    def __eq__(self, other):
        if isinstance(other, Term):
            return self.type == other.type and self.value == other.value
        return False

    def __hash__(self):
        return hash(self.serialize())

class ResponseFormat(str, Enum):
    ANY = "any"
    REGEX = "regex"
    FAIR = "fair"
    
class ResponseOptions(BaseModel):
    format: Optional[ResponseFormat] = None
    
    model_config = {"use_enum_values": True}

class ExecutionOptions(BaseModel):
    timeout: Optional[int] = None
    
class RequestOptions(BaseModel):
    schema_version: int = 1
    response: Optional[ResponseOptions] = None
    execution: Optional[ExecutionOptions] = None
    
    @classmethod
    def from_args(cls, response_format: ResponseFormat = None, execution_timeout: int = None) -> "RequestOptions | None":
        response = None
        if response_format:
            response=ResponseOptions(format=response_format)
        execution = None
        if execution_timeout:
            execution=ExecutionOptions(timeout=execution_timeout)
        if response or execution:
            return cls(response=response, execution=execution)
        else:
            return None
    
class MultiTermsRequest(BaseModel):
    terms: List[Term]
    options: Optional[RequestOptions] = None

class RepeatRequest(BaseModel):
    term: Term
    min: int
    max: Optional[int]
    options: Optional[RequestOptions] = None

class GenerateStringsRequest(BaseModel):
    term: Term
    count: int
    options: Optional[RequestOptions] = None