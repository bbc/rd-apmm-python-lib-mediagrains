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

from .cogenums import CogFrameFormat, CogAudioFormat, CogFrameLayout

from typing import Any, Union, SupportsBytes, Sequence, Mapping, List, Optional, Awaitable, Callable, TYPE_CHECKING
from typing_extensions import TypedDict, Literal

from decimal import Decimal
from numbers import Rational
from fractions import Fraction
from uuid import UUID
from mediatimestamp.immutable import TimeOffset, TimeRange, Timestamp


if TYPE_CHECKING:
    from .grain import GRAIN  # noqa: F401


__all__ = ["RationalTypes",
           "MediaJSONSerialisable",
           "EventGrainDatumDict",
           "GrainMetadataDict",
           "EmptyGrainMetadataDict",
           "AudioGrainMetadataDict",
           "CodedAudioGrainMetadataDict",
           "VideoGrainMetadataDict",
           "EventGrainMetadataDict",
           "FractionDict",
           "GrainDataType",
           "GrainDataParameterType",
           "ParseGrainType"]

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


# This type defines a dictionary that can be converted into a Fraction by mediaJSON

class FractionDict (TypedDict):
    numerator: int
    denominator: int


class TimeLabel (TypedDict, total=False):
    tag: str
    count: int
    rate: FractionDict
    drop_frame: bool


# This is the type that defines what can go in a grain metadata dict.
class _GrainGrainMetadataDict_common_MANDATORY (TypedDict):
    source_id: Union[str, UUID]
    flow_id: Union[str, UUID]
    origin_timestamp: Union[str, Timestamp]
    sync_timestamp: Union[str, Timestamp]
    creation_timestamp: Union[str, Timestamp]
    rate: Union[RationalTypes, Fraction, FractionDict]
    duration: Union[RationalTypes, Fraction, FractionDict]


class _GrainGrainMetadataDict_common (_GrainGrainMetadataDict_common_MANDATORY, total=False):
    timelabels: List[TimeLabel]


class EmptyGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['empty']


class _GrainGrainMetadataDict_cogaudio (TypedDict):
    format: Union[int, CogAudioFormat]  # noqa: E701
    samples: int
    channels: int
    sample_rate: int


class _GrainGrainMetadataDict_cogcodedaudio (_GrainGrainMetadataDict_cogaudio):
    priming: int
    remainder: int


class AudioGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['audio']
    cog_audio: _GrainGrainMetadataDict_cogaudio


class CodedAudioGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['coded_audio']
    cog_coded_audio: _GrainGrainMetadataDict_cogcodedaudio


class VideoGrainComponentDict(TypedDict):
    stride: int
    offset: int
    width: int
    height: int
    length: int


class _GrainGrainMetadataDict_cogframe_MANDATORY (TypedDict):
    format: Union[int, CogFrameFormat]  # noqa: E701
    width: int
    height: int
    layout: Union[int, CogFrameLayout]
    extension: int
    components: List[VideoGrainComponentDict]


class _GrainGrainMetadataDict_cogframe (_GrainGrainMetadataDict_cogframe_MANDATORY, total=False):
    source_aspect_ratio: Union[FractionDict, Fraction, RationalTypes]
    pixel_aspect_ratio: Union[FractionDict, Fraction, RationalTypes]


class VideoGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['video']
    cog_frame: _GrainGrainMetadataDict_cogframe


class _GrainGrainMetadataDict_cogcodedframe_MANDATORY (TypedDict):
    format: Union[int, CogFrameFormat]  # noqa: E701
    origin_width: int
    origin_height: int
    coded_width: int
    coded_height: int
    layout: Union[int, CogFrameLayout]
    is_key_frame: bool
    temporal_offset: int


class _GrainGrainMetadataDict_cogcodedframe (_GrainGrainMetadataDict_cogcodedframe_MANDATORY, total=False):
    unit_offsets: Sequence[int]
    length: int


class CodedVideoGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['coded_video']
    cog_coded_frame: _GrainGrainMetadataDict_cogcodedframe


class _GrainGrainMetadataDict_eventpayload (TypedDict):
    type: str
    topic: str
    data: List[EventGrainDatumDict]


class EventGrainGrainMetadataDict (_GrainGrainMetadataDict_common):
    grain_type: Literal['event']
    event_payload: _GrainGrainMetadataDict_eventpayload


class _EmptyGrainMetadataDict_MANDATORY(TypedDict):
    grain: EmptyGrainGrainMetadataDict


class _AudioGrainMetadataDict_MANDATORY(TypedDict):
    grain: AudioGrainGrainMetadataDict


class _CodedAudioGrainMetadataDict_MANDATORY(TypedDict):
    grain: CodedAudioGrainGrainMetadataDict


class _VideoGrainMetadataDict_MANDATORY(TypedDict):
    grain: VideoGrainGrainMetadataDict


class _CodedVideoGrainMetadataDict_MANDATORY(TypedDict):
    grain: CodedVideoGrainGrainMetadataDict


class _EventGrainMetadataDict_MANDATORY(TypedDict):
    grain: EventGrainGrainMetadataDict


_GrainMetadataDict_OPTIONAL = TypedDict("_GrainMetadataDict_OPTIONAL", {"@_ns": str}, total=False)


class EmptyGrainMetadataDict(_EmptyGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


class AudioGrainMetadataDict(_AudioGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


class CodedAudioGrainMetadataDict(_CodedAudioGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


class VideoGrainMetadataDict(_VideoGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


class CodedVideoGrainMetadataDict(_CodedVideoGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


class EventGrainMetadataDict(_EventGrainMetadataDict_MANDATORY, _GrainMetadataDict_OPTIONAL):
    pass


GrainMetadataDict = Union[
    EmptyGrainMetadataDict,
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    VideoGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    EventGrainMetadataDict]


# This is the type that defines what can go in a grain data element, there may be some corner cases not covered by this
GrainDataType = Union[SupportsBytes, bytes]

GrainDataParameterType = Optional[Union[GrainDataType, Awaitable[Optional[GrainDataType]]]]


# This is the type of a function that can be called to construct a GRAIN object from a metadata dict and a data parameter
ParseGrainType = Callable[[GrainMetadataDict, GrainDataParameterType], "GRAIN"]
