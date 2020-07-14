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
The submodule of mediagrains which contains the actual classes used to
represent grains. In general these classes do not need to be used
directly by client code, but their documentation may be instructive.
"""

from uuid import UUID
from mediatimestamp.immutable import (
    Timestamp,
    TimeOffset,
    TimeRange,
    SupportsMediaTimeOffset,
    SupportsMediaTimestamp,
    mediatimeoffset,
    mediatimestamp)
from collections.abc import Sequence, MutableSequence, Mapping
from fractions import Fraction
from copy import copy, deepcopy
from inspect import isawaitable

from typing import (
    List,
    Dict,
    Any,
    Union,
    SupportsBytes,
    Optional,
    overload,
    Tuple,
    cast,
    Sized,
    Iterator,
    Iterable,
    Awaitable,
    Generator)
from typing_extensions import Literal
from .typing import (
    RationalTypes,
    MediaJSONSerialisable,
    EventGrainDatumDict,
    GrainMetadataDict,
    GrainDataType,
    VideoGrainComponentDict,
    EmptyGrainMetadataDict,
    FractionDict,
    TimeLabel,
    EventGrainMetadataDict,
    VideoGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    GrainDataParameterType)

from .cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat

import json

__all__ = ["GRAIN", "VIDEOGRAIN", "AUDIOGRAIN", "CODEDVIDEOGRAIN", "CODEDAUDIOGRAIN", "EVENTGRAIN", "attributes_for_grain_type"]


def _stringify_timestamp_input(value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> str:
    if isinstance(value, SupportsMediaTimestamp):
        value = mediatimestamp(value).to_sec_nsec()
    elif isinstance(value, SupportsMediaTimeOffset):
        value = mediatimeoffset(value).to_sec_nsec()
    elif not isinstance(value, str):
        raise ValueError(f"{repr(value)} is not a type that can be converted to a Timestamp or TimeOffset, nor is it a string.")

    return value


def attributes_for_grain_type(grain_type: str) -> List[str]:
    """Returns a list of attributes for a partiggcular grain type. Useful for testing."""

    COMMON_ATTRS = ['source_id', 'flow_id', 'origin_timestamp', 'sync_timestamp', 'creation_timestamp', 'rate', 'duration']

    if grain_type == "event":
        return COMMON_ATTRS + ["event_type", "topic", "event_data"]
    elif grain_type == "audio":
        return COMMON_ATTRS + ["format", "samples", "channels", "sample_rate"]
    elif grain_type == "coded_audio":
        return COMMON_ATTRS + ["format", "samples", "channels", "sample_rate", "priming", "remainder"]
    elif grain_type == "video":
        return COMMON_ATTRS + ["format", "width", "height", "layout"]
    elif grain_type == "coded_video":
        return COMMON_ATTRS + ["format", "coded_width", "coded_height", "layout", "origin_width", "origin_height", "is_key_frame", "temporal_offset",
                               "unit_offsets"]
    else:
        return COMMON_ATTRS


class GRAIN(Sequence):
    """\
A class representing a generic media grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is None or one of the following:
* a bytes-like object
* An object supporting the __bytes__ magic method
* An awaitable returning a valid data element

In addition the class provides a number of properties which can be used to
access parts of the standard grain metadata, and all other grain classes
inherit these:

meta
    The meta dictionary object

data
    One of the following:
        * A byteslike object -- This becomes the grain's data element
        * An object that has a method __bytes__ which returns a bytes-like object, which will be the grain's data element
        * None -- This grain has no data

    If the data parameter passed on construction is an awaitable which will return a valid data element when awaited then the grain's data element is
    initially None, but the grain can be awaited to populate it

    For convenience any grain can be awaited and will return the data element, regardless of whether the underlying data is asynchronous or not

    For additional convenience using a grain as an async context manager will ensure that the data element is populated if it needs to be and can be.

grain_type
    A string containing the type of the grain, any value is possible

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data property, or 0 if it is None

expected_length
    How long the data would be expected to be based on what's listed in the metadata


In addition these methods are provided for convenience:


final_origin_timestamp()
    The origin timestamp of the final sample in the grain. For most grain types this is the same as
    origin_timestamp, but not for audio grains.

origin_timerange()
    The origin time range covered by the samples in the grain.

normalise_time(value)
    Returns a normalised Timestamp, TimeOffset or TimeRange using the media rate.

media_rate
    The video frame rate or audio sample rate as a Fraction or None. Returns None if there is no media
    rate or the media rate == 0.

    """
    def __init__(self, meta: GrainMetadataDict, data: GrainDataParameterType):
        self.meta = meta

        self._data_fetcher_coroutine: Optional[Awaitable[Optional[GrainDataType]]]
        self._data_fetcher_length: int = 0
        self._data: Optional[GrainDataType]

        if isawaitable(data):
            self._data_fetcher_coroutine = cast(Awaitable[Optional[GrainDataType]], data)
            self._data = None
        else:
            self._data_fetcher_coroutine = None
            self._data = cast(Optional[GrainDataType], data)
        self._factory = "Grain"

        # This code is here to deal with malformed inputs, and as such needs to cast away the type safety to operate
        if "@_ns" not in self.meta:
            cast(EmptyGrainMetadataDict, self.meta)['@_ns'] = "urn:x-ipstudio:ns:0.1"
        if 'grain' not in self.meta:
            cast(dict, self.meta)['grain'] = {}
        if 'grain_type' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['grain_type'] = "empty"
        if 'creation_timestamp' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = str(Timestamp.get_time())
        if 'origin_timestamp' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['origin_timestamp'] = self.meta['grain']['creation_timestamp']
        if 'sync_timestamp' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = self.meta['grain']['origin_timestamp']
        if 'rate' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {'numerator': 0,
                                                                        'denominator': 1}
        if 'duration' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {'numerator': 0,
                                                                            'denominator': 1}
        if 'source_id' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = "00000000-0000-0000-0000-000000000000"
        if 'flow_id' not in self.meta['grain']:
            cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = "00000000-0000-0000-0000-000000000000"

        if isinstance(self.meta["grain"]["source_id"], UUID):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = str(self.meta['grain']['source_id'])
        if isinstance(self.meta["grain"]["flow_id"], UUID):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = str(self.meta['grain']['flow_id'])
        if not isinstance(self.meta["grain"]["origin_timestamp"], str):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['origin_timestamp'] = _stringify_timestamp_input(self.meta['grain']['origin_timestamp'])
        if not isinstance(self.meta["grain"]["sync_timestamp"], str):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = _stringify_timestamp_input(self.meta['grain']['sync_timestamp'])
        if not isinstance(self.meta["grain"]["creation_timestamp"], str):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = _stringify_timestamp_input(self.meta['grain']['creation_timestamp'])
        if isinstance(self.meta['grain']['rate'], Fraction):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {'numerator': self.meta['grain']['rate'].numerator,
                                                                        'denominator': self.meta['grain']['rate'].denominator}
        if isinstance(self.meta['grain']['duration'], Fraction):
            cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {'numerator': self.meta['grain']['duration'].numerator,
                                                                            'denominator': self.meta['grain']['duration'].denominator}

    def __len__(self) -> int:
        return 2

    @overload
    def __getitem__(self, index: int) -> Union[GrainMetadataDict, Optional[GrainDataType]]: ...

    @overload  # noqa: F811
    def __getitem__(self, index: slice) -> Union[Tuple[GrainMetadataDict],
                                                 Tuple[GrainMetadataDict, Optional[GrainDataType]],
                                                 Tuple[Optional[GrainDataType]],
                                                 Tuple[()]]: ...

    def __getitem__(self, index):  # noqa: F811
        return (self.meta, self.data)[index]

    def __repr__(self) -> str:
        if not hasattr(self.data, "__len__"):
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< binary data of length {} >)".format(self._factory, self.meta, len(cast(Sized, self.data)))

    def __eq__(self, other: object) -> bool:
        return tuple(self) == other

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __copy__(self) -> "GRAIN":
        from .grain_constructors import Grain
        return Grain(copy(self.meta), self.data)

    def __deepcopy__(self, memo) -> "GRAIN":
        from .grain_constructors import Grain
        return Grain(deepcopy(self.meta), deepcopy(self.data))

    def __bytes__(self) -> Optional[bytes]:
        if isinstance(self._data, bytes):
            return self._data
        elif self._data is None:
            return None
        return bytes(self._data)

    def has_data(self) -> bool:
        return self._data is not None

    def __await__(self) -> Generator[Any, None, Optional[GrainDataType]]:
        async def __inner():
            if self._data is None and self._data_fetcher_coroutine is not None:
                self._data = await self._data_fetcher_coroutine
            return self._data
        return __inner().__await__()

    async def __aenter__(self):
        await self
        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    @property
    def data(self) -> Optional[GrainDataType]:
        return self._data

    @data.setter
    def data(self, value: GrainDataParameterType):
        if isawaitable(value):
            self._data = None
            self._data_fetcher_coroutine = cast(Awaitable[Optional[GrainDataType]], value)
        else:
            self._data = cast(Optional[GrainDataType], value)
            self._data_fetcher_coroutine = None

    @property
    def grain_type(self) -> str:
        return self.meta['grain']['grain_type']

    @grain_type.setter
    def grain_type(self, value: str) -> None:
        # We ignore the type safety rules for this assignment
        self.meta['grain']['grain_type'] = value  # type: ignore

    @property
    def source_id(self) -> UUID:
        # Our code ensures that this will always be a string at runtime
        return UUID(cast(str, self.meta['grain']['source_id']))

    @source_id.setter
    def source_id(self, value: Union[UUID, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = str(value)

    @property
    def flow_id(self) -> UUID:
        return UUID(cast(str, self.meta['grain']['flow_id']))

    @flow_id.setter
    def flow_id(self, value: Union[UUID, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = str(value)

    @property
    def origin_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['origin_timestamp']))

    @origin_timestamp.setter
    def origin_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]):
        cast(EmptyGrainMetadataDict, self.meta)['grain']['origin_timestamp'] = _stringify_timestamp_input(value)

    def final_origin_timestamp(self) -> Timestamp:
        return self.origin_timestamp

    def origin_timerange(self) -> TimeRange:
        return TimeRange(self.origin_timestamp, self.final_origin_timestamp(), TimeRange.INCLUSIVE)

    @overload
    def normalise_time(self, value: TimeOffset) -> TimeOffset: ...

    @overload
    def normalise_time(self, value: TimeRange) -> TimeRange: ...

    def normalise_time(self, value):
        if self.media_rate is not None:
            return value.normalise(self.media_rate.numerator, self.media_rate.denominator)
        else:
            return value

    @property
    def media_rate(self) -> Optional[Fraction]:
        return None

    @property
    def sync_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['sync_timestamp']))

    @sync_timestamp.setter
    def sync_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = _stringify_timestamp_input(value)

    @property
    def creation_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['creation_timestamp']))

    @creation_timestamp.setter
    def creation_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = _stringify_timestamp_input(value)

    @property
    def rate(self) -> Fraction:
        return Fraction(cast(FractionDict, self.meta['grain']['rate'])['numerator'],
                        cast(FractionDict, self.meta['grain']['rate'])['denominator'])

    @rate.setter
    def rate(self, value: RationalTypes) -> None:
        value = Fraction(value)
        cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
        }

    @property
    def duration(self) -> Fraction:
        return Fraction(cast(FractionDict, self.meta['grain']['duration'])['numerator'],
                        cast(FractionDict, self.meta['grain']['duration'])['denominator'])

    @duration.setter
    def duration(self, value: RationalTypes) -> None:
        value = Fraction(value)
        cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
        }

    @property
    def timelabels(self) -> "GRAIN.TIMELABELS":
        return GRAIN.TIMELABELS(self)

    @timelabels.setter
    def timelabels(self, value: "Union[List[GRAIN.TIMELABEL], GRAIN.TIMELABELS]") -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['timelabels'] = []
        for x in value:
            self.timelabels.append(x)

    def add_timelabel(self, tag: str, count: int, rate: Fraction, drop_frame: bool = False) -> None:
        tl = GRAIN.TIMELABEL()
        tl.tag = tag
        tl.count = count
        tl.rate = rate
        tl.drop_frame = drop_frame
        self.timelabels.append(tl)

    class TIMELABEL(Mapping):
        GrainMetadataDict = Dict[str, Any]

        def __init__(self, meta: "Optional[GRAIN.TIMELABEL.GrainMetadataDict]" = None):
            if meta is None:
                meta = {}
            self.meta = meta
            if 'tag' not in self.meta:
                self.meta['tag'] = ''
            if 'timelabel' not in self.meta:
                self.meta['timelabel'] = {}
            if 'frames_since_midnight' not in self.meta['timelabel']:
                self.meta['timelabel']['frames_since_midnight'] = 0
            if 'frame_rate_numerator' not in self.meta['timelabel']:
                self.meta['timelabel']['frame_rate_numerator'] = 0
            if 'frame_rate_denominator' not in self.meta['timelabel']:
                self.meta['timelabel']['frame_rate_denominator'] = 1
            if 'drop_frame' not in self.meta['timelabel']:
                self.meta['timelabel']['drop_frame'] = False

        def __getitem__(self, key: str) -> Union[str, Dict[str, Union[int, bool]]]:
            return self.meta[key]

        def __setitem__(self, key: str, value: Union[str, Dict[str, Union[int, bool]]]) -> None:
            if key not in ['tag', 'timelabel']:
                raise KeyError
            self.meta[key] = value

        def __iter__(self) -> Iterator[str]:
            return self.meta.__iter__()

        def __len__(self) -> int:
            return 2

        def __eq__(self, other: object) -> bool:
            return dict(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        @property
        def tag(self) -> str:
            return self.meta['tag']

        @tag.setter
        def tag(self, value: str) -> None:
            self.meta['tag'] = value

        @property
        def count(self) -> int:
            return self.meta['timelabel']['frames_since_midnight']

        @count.setter
        def count(self, value: int) -> None:
            self.meta['timelabel']['frames_since_midnight'] = int(value)

        @property
        def rate(self) -> Fraction:
            return Fraction(self.meta['timelabel']['frame_rate_numerator'],
                            self.meta['timelabel']['frame_rate_denominator'])

        @rate.setter
        def rate(self, value: RationalTypes) -> None:
            value = Fraction(value)
            self.meta['timelabel']['frame_rate_numerator'] = value.numerator
            self.meta['timelabel']['frame_rate_denominator'] = value.denominator

        @property
        def drop_frame(self) -> bool:
            return self.meta['timelabel']['drop_frame']

        @drop_frame.setter
        def drop_frame(self, value: bool) -> None:
            self.meta['timelabel']['drop_frame'] = bool(value)

    class TIMELABELS(MutableSequence):
        def __init__(self, parent: "GRAIN"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> "GRAIN.TIMELABEL": ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> "List[GRAIN.TIMELABEL]": ...

        def __getitem__(self, key):  # noqa: F811
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list index out of range")
            if isinstance(key, int):
                return GRAIN.TIMELABEL(self.parent.meta['grain']['timelabels'][key])
            else:
                return [GRAIN.TIMELABEL(self.parent.meta['grain']['timelabels'][n]) for n in range(len(self))[key]]

        @overload
        def __setitem__(self, key: int, value: "GRAIN.TIMELABEL.GrainMetadataDict") -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: "Iterable[GRAIN.TIMELABEL.GrainMetadataDict]") -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")
            if isinstance(key, int):
                self.parent.meta['grain']['timelabels'][key] = dict(GRAIN.TIMELABEL(value))
            else:
                values = iter(value)
                for n in key:
                    self.parent.meta['grain']['timelabels'][n] = dict(GRAIN.TIMELABEL(next(values)))

        def __delitem__(self, key: Union[int, slice]) -> None:
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")

            del self.parent.meta['grain']['timelabels'][key]
            if len(self.parent.meta['grain']['timelabels']) == 0:
                del self.parent.meta['grain']['timelabels']

        def insert(self, key: int, value: "GRAIN.TIMELABEL.GrainMetadataDict") -> None:
            if 'timelabels' not in self.parent.meta['grain']:
                cast(EmptyGrainMetadataDict, self.parent.meta)['grain']['timelabels'] = []
            self.parent.meta['grain']['timelabels'].insert(key, cast(TimeLabel, dict(GRAIN.TIMELABEL(value))))

        def __len__(self) -> int:
            if 'timelabels' not in self.parent.meta['grain']:
                return 0
            return len(self.parent.meta['grain']['timelabels'])

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

    @property
    def length(self) -> int:
        if hasattr(self.data, "__len__"):
            return len(cast(Sized, self.data))
        elif hasattr(self.data, "__bytes__"):
            return len(bytes(cast(SupportsBytes, self.data)))
        elif self.data is None and self._data_fetcher_coroutine is not None:
            return self._data_fetcher_length
        else:
            return 0

    @length.setter
    def length(self, L: int) -> None:
        if self.data is None and self._data_fetcher_coroutine is not None:
            self._data_fetcher_length = L
        else:
            raise AttributeError

    @property
    def expected_length(self) -> int:
        if 'length' in self.meta['grain']:
            return cast(dict, self.meta['grain'])['length']
        else:
            return self.length


class EVENTGRAIN(GRAIN):
    """\
A class representing an event grain.

Any grain can be freely cast to a tuple:

  (meta, None)

where meta is a dictionary containing the grain metadata.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "event"

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    the length of the json representation in data

The EventGrain class also provides additional properies

event_type
    A urn representing the type of the event

topic
    A string which should be an identifier for the topic of the event

event_data
    A list-like sequence object of EVENTGRAIN.DATA objects representing the
    data in the event

And the class provides one additional method:

append(path, pre=None, post=None)
    Adds a new data element to the event_data property with path set to the
    provided string, and pre and post set optionally. All calls should use
    only json serialisable objects for the values of pre and post.
    """
    def __init__(self, meta: EventGrainMetadataDict, data: GrainDataParameterType):
        super(EVENTGRAIN, self).__init__(meta, None)
        self.meta: EventGrainMetadataDict

        self._factory = "EventGrain"
        self.meta['grain']['grain_type'] = 'event'
        if 'event_payload' not in self.meta['grain']:
            self.meta['grain']['event_payload'] = {
                'type': "",
                'topic': "",
                'data': []}
        if isawaitable(data):
            self._data_fetcher_coroutine = cast(Awaitable[Optional[GrainDataType]], data)
        elif data is not None:
            if isinstance(data, bytes):
                self.data = data
            else:
                self.data = bytes(cast(SupportsBytes, data))
        if 'type' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['type'] = ""
        if 'topic' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['topic'] = ""
        if 'data' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['data'] = []

    @property
    def data(self) -> bytes:
        return json.dumps({'type': self.event_type,
                           'topic': self.topic,
                           'data': [dict(datum) for datum in self.event_data]}).encode('utf-8')

    @data.setter
    def data(self, value: Union[str, bytes]):
        if not isinstance(value, str):
            payload = json.loads(value.decode('utf-8'))
        else:
            payload = json.loads(value)

        if 'type' not in payload or 'topic' not in payload or 'data' not in payload:
            raise ValueError("incorrectly formated event payload")
        self.event_type = payload['type']
        self.topic = payload['topic']
        self.meta['grain']['event_payload']['data'] = []
        for datum in payload['data']:
            d: EventGrainDatumDict = {'path': datum['path']}
            if 'pre' in datum:
                d['pre'] = datum['pre']
            if 'post' in datum:
                d['post'] = datum['post']
            self.meta['grain']['event_payload']['data'].append(d)

    def __repr__(self) -> str:
        return "EventGrain({!r})".format(self.meta)

    @property
    def event_type(self) -> str:
        return self.meta['grain']['event_payload']['type']

    @event_type.setter
    def event_type(self, value: str) -> None:
        self.meta['grain']['event_payload']['type'] = value

    @property
    def topic(self) -> str:
        return self.meta['grain']['event_payload']['topic']

    @topic.setter
    def topic(self, value: str) -> None:
        self.meta['grain']['event_payload']['topic'] = value

    class DATA(Mapping):
        """\
A class representing a data element within an event grain.

It can be trated as a dictionary:

    {"path": "/a/path",
     "pre": <json serialisable object>,
     "post": <json serialisable object>}

But also provides additional properties:

path
    The path

pre
    The pre value, or None if none is present. If set to None will remove "pre"
    key from dictionary.

post
    The post value, or None if none is present. If set to None will remove
    "post" key from dictionary.
"""
        def __init__(self, meta: EventGrainDatumDict):
            self.meta = meta

        def __getitem__(self, key: Literal['path', 'pre', 'post']) -> MediaJSONSerialisable:
            return self.meta[key]

        def __setitem__(self, key: Literal['path', 'pre', 'post'], value: MediaJSONSerialisable) -> None:
            self.meta[key] = value

        def __delitem__(self, key: Literal['pre', 'post']) -> None:
            del self.meta[key]

        def __iter__(self) -> Iterator[str]:
            return self.meta.__iter__()

        def __len__(self) -> int:
            return self.meta.__len__()

        def __eq__(self, other: object) -> bool:
            return dict(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        @property
        def path(self) -> str:
            return self.meta['path']

        @path.setter
        def path(self, value: str) -> None:
            self.meta['path'] = value

        @property
        def pre(self) -> Optional[MediaJSONSerialisable]:
            if 'pre' in self.meta:
                return self.meta['pre']
            else:
                return None

        @pre.setter
        def pre(self, value: Optional[MediaJSONSerialisable]) -> None:
            if value is not None:
                self.meta['pre'] = value
            else:
                del self.meta['pre']

        @property
        def post(self) -> Optional[MediaJSONSerialisable]:
            if 'post' in self.meta:
                return self.meta['post']
            else:
                return None

        @post.setter
        def post(self, value: Optional[MediaJSONSerialisable]) -> None:
            if value is not None:
                self.meta['post'] = value
            elif 'post' in self.meta:
                del self.meta['post']

    @property
    def event_data(self) -> List["EVENTGRAIN.DATA"]:
        return [EVENTGRAIN.DATA(datum) for datum in self.meta['grain']['event_payload']['data']]

    @event_data.setter
    def event_data(self, value: List[EventGrainDatumDict]) -> None:
        self.meta['grain']['event_payload']['data'] = [cast(EventGrainDatumDict, dict(datum)) for datum in value]

    def append(self, path: str, pre: Optional[MediaJSONSerialisable] = None, post: Optional[MediaJSONSerialisable] = None) -> None:
        datum = EventGrainDatumDict(path=path)
        if pre is not None:
            datum['pre'] = pre
        if post is not None:
            datum['post'] = post
        self.meta['grain']['event_payload']['data'].append(datum)


class VIDEOGRAIN(GRAIN):
    """\
A class representing a raw video grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is the data element described below.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "video"

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data element or 0 if that is None

The VideoGrain class also provides additional properies

format
    An enumerated value of type CogFrameFormat

width
    The video width in pixels

height
    The video height in pixels

layout
    An enumerated value of type CogFrameLayout

extension
    A numeric value indicating the offset from the start of the data array to
    the start of the actual data, usually 0.

source_aspect_ratio
    A fractions.Fraction object indicating the video source aspect ratio, or None

pixel_aspect_ratio
    A fractions.Fraction object indicating the video pixel aspect ratio, or None

components
    A list-like sequence of VIDEOGRAIN.COMPONENT objects
    """

    class COMPONENT(Mapping):
        """
A class representing a video component, it may be treated as a dictionary of the form:

    {"stride": <an integer>,
     "offset": <an integer>,
     "width": <an integer>,
     "height": <an integer>,
     "length": <an integer>}

with additional properties allowing access to the members:

stride
    The offset in bytes between the first data byte of each line in the data
    array and the first byte of the next.

offset
    The offset in bytes from the start of the data array to the first byte of
    the first line of the data in this component.

width
    The number of samples per line in this component

height
    The number of lines in this component

length
    The total length of the data for this component in bytes
"""
        def __init__(self, meta: VideoGrainComponentDict):
            self.meta = meta

        def __getitem__(self, key: Literal['stride', 'offset', 'width', 'height', 'length']) -> int:
            return self.meta[key]

        def __setitem__(self, key: Literal['stride', 'offset', 'width', 'height', 'length'], value: int) -> None:
            self.meta[key] = value

        def __iter__(self) -> Iterator[str]:
            return self.meta.__iter__()

        def __len__(self) -> int:
            return self.meta.__len__()

        def __eq__(self, other: object) -> bool:
            return dict(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        @property
        def stride(self) -> int:
            return self.meta['stride']

        @stride.setter
        def stride(self, value: int) -> None:
            self.meta['stride'] = value

        @property
        def offset(self) -> int:
            return self.meta['offset']

        @offset.setter
        def offset(self, value: int) -> None:
            self.meta['offset'] = value

        @property
        def width(self) -> int:
            return self.meta['width']

        @width.setter
        def width(self, value: int) -> None:
            self.meta['width'] = value

        @property
        def height(self) -> int:
            return self.meta['height']

        @height.setter
        def height(self, value: int) -> None:
            self.meta['height'] = value

        @property
        def length(self) -> int:
            return self.meta['length']

        @length.setter
        def length(self, value: int) -> None:
            self.meta['length'] = value

    class COMPONENT_LIST(MutableSequence):
        def __init__(self, parent: "VIDEOGRAIN"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> "VIDEOGRAIN.COMPONENT": ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> "List[VIDEOGRAIN.COMPONENT]": ...

        def __getitem__(self, key):  # noqa: F811
            if isinstance(key, int):
                return type(self.parent).COMPONENT(self.parent.meta['grain']['cog_frame']['components'][key])
            else:
                return [type(self.parent).COMPONENT(self.parent.meta['grain']['cog_frame']['components'][k]) for k in range(len(self))[key]]

        @overload
        def __setitem__(self, key: int, value: VideoGrainComponentDict) -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: Iterable[VideoGrainComponentDict]) -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if isinstance(key, int):
                self.parent.meta['grain']['cog_frame']['components'][key] = type(self.parent).COMPONENT(value)
            else:
                values = iter(value)
                for n in range(len(self))[key]:
                    self.parent.meta['grain']['cog_frame']['components'][n] = type(self.parent).COMPONENT(next(values))

        def __delitem__(self, key: Union[int, slice]) -> None:
            del self.parent.meta['grain']['cog_frame']['components'][key]

        def insert(self, key: int, value: VideoGrainComponentDict) -> None:
            self.parent.meta['grain']['cog_frame']['components'].insert(key, type(self.parent).COMPONENT(value))  # type: ignore

        def __len__(self) -> int:
            return len(self.parent.meta['grain']['cog_frame']['components'])

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

    def __init__(self, meta: VideoGrainMetadataDict, data: GrainDataParameterType):
        super(VIDEOGRAIN, self).__init__(meta, data)
        self.meta: VideoGrainMetadataDict

        self._factory = "VideoGrain"
        self.meta['grain']['grain_type'] = 'video'
        if 'cog_frame' not in self.meta['grain']:
            self.meta['grain']['cog_frame'] = {
                'format': int(CogFrameFormat.UNKNOWN),
                'width': 0,
                'height': 0,
                'layout': int(CogFrameLayout.UNKNOWN),
                'extension': 0,
                'components': []
            }
        self.meta['grain']['cog_frame']['format'] = int(self.meta['grain']['cog_frame']['format'])
        self.meta['grain']['cog_frame']['layout'] = int(self.meta['grain']['cog_frame']['layout'])
        self.components = VIDEOGRAIN.COMPONENT_LIST(self)

    @property
    def format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_frame']['format'])

    @format.setter
    def format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_frame']['format'] = int(value)

    @property
    def width(self) -> int:
        return self.meta['grain']['cog_frame']['width']

    @width.setter
    def width(self, value: int) -> None:
        self.meta['grain']['cog_frame']['width'] = value

    @property
    def height(self) -> int:
        return self.meta['grain']['cog_frame']['height']

    @height.setter
    def height(self, value: int) -> None:
        self.meta['grain']['cog_frame']['height'] = value

    @property
    def layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_frame']['layout'])

    @layout.setter
    def layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_frame']['layout'] = int(value)

    @property
    def extension(self) -> int:
        return self.meta['grain']['cog_frame']['extension']

    @extension.setter
    def extension(self, value: int) -> None:
        self.meta['grain']['cog_frame']['extension'] = value

    @property
    def source_aspect_ratio(self) -> Optional[Fraction]:
        if 'source_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(cast(FractionDict, self.meta['grain']['cog_frame']['source_aspect_ratio'])['numerator'],
                            cast(FractionDict, self.meta['grain']['cog_frame']['source_aspect_ratio'])['denominator'])
        else:
            return None

    @source_aspect_ratio.setter
    def source_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_frame']['source_aspect_ratio'] = {'numerator': value.numerator,
                                                                  'denominator': value.denominator}

    @property
    def pixel_aspect_ratio(self) -> Optional[Fraction]:
        if 'pixel_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(cast(FractionDict, self.meta['grain']['cog_frame']['pixel_aspect_ratio'])['numerator'],
                            cast(FractionDict, self.meta['grain']['cog_frame']['pixel_aspect_ratio'])['denominator'])
        else:
            return None

    @pixel_aspect_ratio.setter
    def pixel_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_frame']['pixel_aspect_ratio'] = {'numerator': value.numerator,
                                                                 'denominator': value.denominator}

    @property
    def expected_length(self) -> int:
        length = 0
        for component in self.components:
            if component.offset + component.length > length:
                length = component.offset + component.length
        return length

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.rate:
            return self.rate
        else:
            return None


class CODEDVIDEOGRAIN(GRAIN):
    """\
A class representing a coded video grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is the data element described below.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "coded_video"

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data element or 0 if that is None

The CodedVideoGrain class also provides additional properies

format
    An enumerated value of type CogFrameFormat

layout
    An enumerated value of type CogFrameLayout

origin_width
    The original video width in pixels

origin_height
    The original video height in pixels

coded_width
    The coded video width in pixels

coded_height
    The coded video height in pixels

temporal_offset
    A signed integer value indicating the offset from the origin timestamp of
    this grain to the expected presentation time of the picture in frames.

unit_offsets
    A list-like object containing integer offsets of coded units within the
    data array.
"""
    def __init__(self, meta: CodedVideoGrainMetadataDict, data: GrainDataParameterType):
        super(CODEDVIDEOGRAIN, self).__init__(meta, data)
        self.meta: CodedVideoGrainMetadataDict

        self._factory = "CodedVideoGrain"
        self.meta['grain']['grain_type'] = 'coded_video'
        if 'cog_coded_frame' not in self.meta['grain']:
            self.meta['grain']['cog_coded_frame'] = {}  # type: ignore
        if 'format' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['format'] = int(CogFrameFormat.UNKNOWN)
        if 'layout' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['layout'] = int(CogFrameLayout.UNKNOWN)
        if 'origin_width' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['origin_width'] = 0
        if 'origin_height' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['origin_height'] = 0
        if 'coded_width' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['coded_width'] = 0
        if 'coded_height' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['coded_height'] = 0
        if 'temporal_offset' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['temporal_offset'] = 0
        if 'length' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['length'] = 0
        if 'is_key_frame' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['is_key_frame'] = False
        self.meta['grain']['cog_coded_frame']['format'] = int(self.meta['grain']['cog_coded_frame']['format'])
        self.meta['grain']['cog_coded_frame']['layout'] = int(self.meta['grain']['cog_coded_frame']['layout'])

    @property
    def format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])

    @format.setter
    def format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_coded_frame']['format'] = int(value)

    @property
    def layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @layout.setter
    def layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_coded_frame']['layout'] = int(value)

    @property
    def origin_width(self) -> int:
        return self.meta['grain']['cog_coded_frame']['origin_width']

    @origin_width.setter
    def origin_width(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['origin_width'] = value

    @property
    def origin_height(self) -> int:
        return self.meta['grain']['cog_coded_frame']['origin_height']

    @origin_height.setter
    def origin_height(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['origin_height'] = value

    @property
    def coded_width(self) -> int:
        return self.meta['grain']['cog_coded_frame']['coded_width']

    @coded_width.setter
    def coded_width(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['coded_width'] = value

    @property
    def coded_height(self) -> int:
        return self.meta['grain']['cog_coded_frame']['coded_height']

    @coded_height.setter
    def coded_height(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['coded_height'] = value

    @property
    def is_key_frame(self) -> bool:
        return self.meta['grain']['cog_coded_frame']['is_key_frame']

    @is_key_frame.setter
    def is_key_frame(self, value: bool) -> None:
        self.meta['grain']['cog_coded_frame']['is_key_frame'] = bool(value)

    @property
    def temporal_offset(self) -> int:
        return self.meta['grain']['cog_coded_frame']['temporal_offset']

    @temporal_offset.setter
    def temporal_offset(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['temporal_offset'] = value

    class UNITOFFSETS(MutableSequence):
        def __init__(self, parent: "CODEDVIDEOGRAIN"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> int: ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> List[int]: ...

        def __getitem__(self, key):  # noqa: F811
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key]
            else:
                raise IndexError("list index out of range")

        @overload
        def __setitem__(self, key: int, value: int) -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: Iterable[int]) -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key] = value
            else:
                raise IndexError("list assignment index out of range")

        def __delitem__(self, key: Union[int, slice]) -> None:
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                del cast(List[int], self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])[key]
                if len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets']) == 0:
                    del self.parent.meta['grain']['cog_coded_frame']['unit_offsets']
            else:
                raise IndexError("list assignment index out of range")

        def insert(self, key: int, value: int) -> None:
            if 'unit_offsets' not in self.parent.meta['grain']['cog_coded_frame']:
                d: List[int] = []
                d.insert(key, value)
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'] = d
            else:
                cast(List[int], self.parent.meta['grain']['cog_coded_frame']['unit_offsets']).insert(key, value)

        def __len__(self) -> int:
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])
            else:
                return 0

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        def __repr__(self) -> str:
            if 'unit_offsets' not in self.parent.meta['grain']['cog_coded_frame']:
                return repr([])
            else:
                return repr(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])

    @property
    def unit_offsets(self) -> "CODEDVIDEOGRAIN.UNITOFFSETS":
        return CODEDVIDEOGRAIN.UNITOFFSETS(self)

    @unit_offsets.setter
    def unit_offsets(self, value: Iterable[int]) -> None:
        if value is not None and not (hasattr(value, "__len__") and len(cast(Sized, value)) == 0):
            self.meta['grain']['cog_coded_frame']['unit_offsets'] = list(value)
        elif 'unit_offsets' in self.meta['grain']['cog_coded_frame']:
            del self.meta['grain']['cog_coded_frame']['unit_offsets']

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.rate:
            return self.rate
        else:
            return None


def size_for_audio_format(cog_audio_format: CogAudioFormat, channels: int, samples: int) -> int:
    if (cog_audio_format & 0x200) == 0x200:  # compressed format, no idea of correct size
        return 0

    if (cog_audio_format & 0x3) == 0x1:
        channels += 1
        channels //= 2
        channels *= 2
    if (cog_audio_format & 0xC) == 0xC:
        depth = 8
    elif (cog_audio_format & 0xf) == 0x04:
        depth = 4
    else:
        depth = ((cog_audio_format & 0xf) >> 2) + 2
    return channels * samples * depth


class AUDIOGRAIN(GRAIN):
    """\
A class representing a raw audio grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is the data element described below..

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "audio"

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data element or 0 if that is None

The AudioGrain class also provides additional properies

format
    An enumerated value of type CogAudioFormat

samples
    The number of audio samples per channel in this grain

channels
    The number of channels in this grain

sample_rate
    An integer indicating the number of samples per channel per second in this
    audio flow.
"""
    def __init__(self, meta: AudioGrainMetadataDict, data: GrainDataParameterType):
        super(AUDIOGRAIN, self).__init__(meta, data)
        self.meta: AudioGrainMetadataDict

        self._factory = "AudioGrain"
        self.meta['grain']['grain_type'] = 'audio'
        if 'cog_audio' not in self.meta['grain']:
            self.meta['grain']['cog_audio'] = {}  # type: ignore
        if 'format' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['format'] = int(CogAudioFormat.INVALID)
        if 'samples' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['samples'] = 0
        if 'channels' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['channels'] = 0
        if 'sample_rate' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['sample_rate'] = 0
        self.meta['grain']['cog_audio']['format'] = int(self.meta['grain']['cog_audio']['format'])

    def final_origin_timestamp(self) -> Timestamp:
        return (self.origin_timestamp + TimeOffset.from_count(self.samples - 1, self.sample_rate, 1))

    @property
    def format(self) -> CogAudioFormat:
        return CogAudioFormat(self.meta['grain']['cog_audio']['format'])

    @format.setter
    def format(self, value: CogAudioFormat) -> None:
        self.meta['grain']['cog_audio']['format'] = int(value)

    @property
    def samples(self) -> int:
        return self.meta['grain']['cog_audio']['samples']

    @samples.setter
    def samples(self, value: int) -> None:
        self.meta['grain']['cog_audio']['samples'] = int(value)

    @property
    def channels(self) -> int:
        return self.meta['grain']['cog_audio']['channels']

    @channels.setter
    def channels(self, value: int) -> None:
        self.meta['grain']['cog_audio']['channels'] = int(value)

    @property
    def sample_rate(self) -> int:
        return self.meta['grain']['cog_audio']['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self.meta['grain']['cog_audio']['sample_rate'] = int(value)

    @property
    def expected_length(self) -> int:
        return size_for_audio_format(self.format, self.channels, self.samples)

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.sample_rate:
            return Fraction(self.sample_rate, 1)
        else:
            return None


class CODEDAUDIOGRAIN(GRAIN):
    """\
A class representing a coded audio grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is a
bytes-like object containing the coded audio data.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "coded_audio"

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data element or 0 if that is None

The AudioGrain class also provides additional properies

format
    An enumerated value of type CogAudioFormat

samples
    The number of audio samples per channel in this grain

channels
    The number of channels in this grain

sample_rate
    An integer indicating the number of samples per channel per second in this
    audio flow.

priming
    An integer

remainder
    An integer
"""
    def __init__(self, meta: CodedAudioGrainMetadataDict, data: GrainDataParameterType):
        super(CODEDAUDIOGRAIN, self).__init__(meta, data)
        self.meta: CodedAudioGrainMetadataDict

        self._factory = "CodedAudioGrain"
        self.meta['grain']['grain_type'] = 'coded_audio'
        if 'cog_coded_audio' not in self.meta['grain']:
            self.meta['grain']['cog_coded_audio'] = {}  # type: ignore
        if 'format' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['format'] = int(CogAudioFormat.INVALID)
        if 'channels' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['channels'] = 0
        if 'samples' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['samples'] = 0
        if 'priming' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['priming'] = 0
        if 'remainder' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['remainder'] = 0
        if 'sample_rate' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['sample_rate'] = 48000
        self.meta['grain']['cog_coded_audio']['format'] = int(self.meta['grain']['cog_coded_audio']['format'])

    def final_origin_timestamp(self) -> Timestamp:
        return (self.origin_timestamp + TimeOffset.from_count(self.samples - 1, self.sample_rate, 1))

    @property
    def format(self) -> CogAudioFormat:
        return CogAudioFormat(self.meta['grain']['cog_coded_audio']['format'])

    @format.setter
    def format(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['format'] = int(value)

    @property
    def channels(self) -> int:
        return self.meta['grain']['cog_coded_audio']['channels']

    @channels.setter
    def channels(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['channels'] = value

    @property
    def samples(self) -> int:
        return self.meta['grain']['cog_coded_audio']['samples']

    @samples.setter
    def samples(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['samples'] = value

    @property
    def priming(self) -> int:
        return self.meta['grain']['cog_coded_audio']['priming']

    @priming.setter
    def priming(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['priming'] = value

    @property
    def remainder(self) -> int:
        return self.meta['grain']['cog_coded_audio']['remainder']

    @remainder.setter
    def remainder(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['remainder'] = value

    @property
    def sample_rate(self) -> int:
        return self.meta['grain']['cog_coded_audio']['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self.meta['grain']['cog_coded_audio']['sample_rate'] = value

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.sample_rate:
            return Fraction(self.sample_rate, 1)
        else:
            return None


if __name__ == "__main__":  # pragma: no cover
    from uuid import uuid1, uuid5
    from .grain_constructors import Grain

    src_id = uuid1()
    flow_id = uuid5(src_id, "flow_id:test_flow")

    grain1 = Grain(src_id, flow_id)
    grain2 = Grain(grain1.meta)
    print(grain1)
    print(grain2)
