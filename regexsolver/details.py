from typing import Any, Optional

from pydantic import BaseModel, model_validator


class Cardinality(BaseModel):
    """
    Class that represent the number of possible values.
    """
    type: str
    value: Optional[int] = None

    def is_infinite(self) -> bool:
        """
        True if it has a infinite number of values, False otherwise.
        """
        return self.type == 'infinite'

    def __str__(self):
        if self.type == 'infinite':
            return "Infinite"
        elif self.type == 'bigInteger':
            return 'BigInteger'
        elif self.type == 'integer':
            return "Integer({})".format(self.value)
        else:
            return 'Unknown'


class Length(BaseModel):
    """
    Contains the minimum and maximum length of possible values.
    """

    minimum: Optional[int]
    maximum: Optional[int]

    @model_validator(mode="before")
    def from_list(cls, values: Any):
        if isinstance(values, dict):
            return {'minimum': values.get('min'), 'maximum': values.get('max')}
        
        if isinstance(values, list):
            if len(values) != 2:
                raise ValueError("List must contain exactly two elements")
            return {'minimum': values[0], 'maximum': values[1]}
        
        return values

    def __str__(self):
        return "Length[minimum={}, maximum={}]".format(
            self.minimum,
            self.maximum
        )


class Details(BaseModel):
    """
    Contains details about the requested Term.
    """
    type: str = 'details'

    cardinality: Cardinality
    length: Length
    empty: bool
    total: bool

    def __str__(self):
        return "Details[cardinality={}, length={}, empty={}, total={}]".format(
            self.cardinality,
            self.length,
            self.empty,
            self.total
        )
