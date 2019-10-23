#
# Copyright 2018 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""\
Types used for type checking other parts of the library
"""

from typing import Any, Union, Dict, SupportsBytes, Sequence, Mapping
from typing_extensions import TypedDict

from decimal import Decimal
from numbers import Rational
from fractions import Fraction
from uuid import UUID
from mediatimestamp.immutable import TimeOffset, TimeRange


__all__ = ["RationalTypes", "MediaJSONSerialisable", "EventGrainDatumDict"]

# These are the types that can be freely converted into a Fraction
RationalTypes = Union[str, float, Decimal, Rational]

# TODO: Move this into mediajson, and make it actually describe what is serialisable.
# At current due to weaknesses in mypy this is rather limited and only provides type safety for a limited depth of json strucure
#
#  Hopefully at some point in the future proper recursive type definitions will be supported
#  Until that time we simply assume none of our json structures are all that deep
_MediaJSONSerialisable_value = Union[str, int, UUID, TimeOffset, TimeRange, Fraction]
_MediaJSONSerialisable0 = Union[_MediaJSONSerialisable_value, Sequence[Any], Mapping[str, Any]]  # This means that type checking stops at the fourth level
_MediaJSONSerialisable1 = Union[_MediaJSONSerialisable_value, Sequence[_MediaJSONSerialisable0], Mapping[str, _MediaJSONSerialisable0]]
_MediaJSONSerialisable2 = Union[_MediaJSONSerialisable_value, Sequence[_MediaJSONSerialisable1], Mapping[str, _MediaJSONSerialisable1]]
_MediaJSONSerialisable3 = Union[_MediaJSONSerialisable_value, Sequence[_MediaJSONSerialisable2], Mapping[str, _MediaJSONSerialisable2]]
_MediaJSONSerialisable4 = Union[_MediaJSONSerialisable_value, Sequence[_MediaJSONSerialisable3], Mapping[str, _MediaJSONSerialisable3]]
MediaJSONSerialisable = _MediaJSONSerialisable4


# This is weird, but is currently how you specifiy a structured dict with optional entries
# This defines what is allowable in a dictionary representation of an EventGrain data element
class _EventGrainDatumDict_MANDATORY (TypedDict):
    path: str


class EventGrainDatumDict (_EventGrainDatumDict_MANDATORY, total=False):
    pre: MediaJSONSerialisable
    post: MediaJSONSerialisable


# This is the type that defines what can go in a grain metadata dict. Right now it is too permissive
GrainMetadataDict = Dict[str, Any]


# This is the type that defines what can go in a grain data element, there may be some corner cases not covered by this
GrainDataType = Union[SupportsBytes, bytes]
