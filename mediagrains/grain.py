#!/usr/bin/python
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
from mediatimestamp.immutable import Timestamp, TimeOffset, TimeRange
from collections.abc import Sequence, MutableSequence, Mapping
from fractions import Fraction
from decimal import Decimal
from numbers import Rational
from copy import copy, deepcopy

from typing import List, Dict, Any, Union, SupportsBytes, Optional, overload, Tuple, cast, Sized, Iterator, Iterable
from typing_extensions import TypedDict, Literal

from .cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat

import json

__all__ = ["GRAIN", "VIDEOGRAIN", "AUDIOGRAIN", "CODEDVIDEOGRAIN", "CODEDAUDIOGRAIN", "EVENTGRAIN", "attributes_for_grain_type"]


# TODO: Move this somewhere more central
# These are the types that can be freely converte into a Fraction
RationalTypes = Union[str, float, Decimal, Rational]

# TODO: Move this into mediajson, and make it actually describe what is serialisable.
MediaJSONSerialisable = Any


# This is weird, but is currently how you specifiy a structured dict with optional entries
class _EventGrainDatumDict_MANDATORY (TypedDict):
    path: str


class EventGrainDatumDict (_EventGrainDatumDict_MANDATORY, total=False):
    pre: MediaJSONSerialisable
    post: MediaJSONSerialisable


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

where meta is a dictionary containing the grain metadata, and data is a python
buffer object representing the payload (or None for an empty grain).

In addition the class provides a number of properties which can be used to
access parts of the standard grain metadata, and all other grain classes
inherit these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

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
    Returns a normalised Timestamp, TimeOffset or TimeRange using the video frame rate or audio sample rate.

    """

    # This is a type that represents a valid metadata dictionary.
    # In future we will constrain this more, right now it's just a Dict[str, Any]
    MetadataDict = Dict[str, Any]
    DataType = Union[SupportsBytes, bytes]

    def __init__(self, meta: MetadataDict, data: Optional[DataType]):
        self.meta = meta
        self._data = data
        self._factory = "Grain"
        if "@_ns" not in self.meta:
            self.meta['@_ns'] = "urn:x-ipstudio:ns:0.1"
        if 'grain' not in self.meta:
            self.meta['grain'] = {}
        if 'grain_type' not in self.meta['grain']:
            self.meta['grain']['grain_type'] = "empty"
        if 'creation_timestamp' not in self.meta['grain']:
            self.meta['grain']['creation_timestamp'] = str(Timestamp.get_time())
        if 'origin_timestamp' not in self.meta['grain']:
            self.meta['grain']['origin_timestamp'] = self.meta['grain']['creation_timestamp']
        if 'sync_timestamp' not in self.meta['grain']:
            self.meta['grain']['sync_timestamp'] = self.meta['grain']['origin_timestamp']
        if 'rate' not in self.meta['grain']:
            self.meta['grain']['rate'] = {'numerator': 0,
                                          'denominator': 1}
        if 'duration' not in self.meta['grain']:
            self.meta['grain']['duration'] = {'numerator': 0,
                                              'denominator': 1}
        if 'source_id' not in self.meta['grain']:
            self.meta['grain']['source_id'] = "00000000-0000-0000-0000-000000000000"
        if 'flow_id' not in self.meta['grain']:
            self.meta['grain']['flow_id'] = "00000000-0000-0000-0000-000000000000"

        if isinstance(self.meta["grain"]["source_id"], UUID):
            self.meta['grain']['source_id'] = str(self.meta['grain']['source_id'])
        if isinstance(self.meta["grain"]["flow_id"], UUID):
            self.meta['grain']['flow_id'] = str(self.meta['grain']['flow_id'])
        if isinstance(self.meta["grain"]["origin_timestamp"], Timestamp):
            self.meta['grain']['origin_timestamp'] = str(self.meta['grain']['origin_timestamp'])
        if isinstance(self.meta["grain"]["sync_timestamp"], Timestamp):
            self.meta['grain']['sync_timestamp'] = str(self.meta['grain']['sync_timestamp'])
        if isinstance(self.meta["grain"]["creation_timestamp"], Timestamp):
            self.meta['grain']['creation_timestamp'] = str(self.meta['grain']['creation_timestamp'])
        if isinstance(self.meta['grain']['rate'], Fraction):
            self.meta['grain']['rate'] = {'numerator': self.meta['grain']['rate'].numerator,
                                          'denominator': self.meta['grain']['rate'].denominator}
        if isinstance(self.meta['grain']['duration'], Fraction):
            self.meta['grain']['duration'] = {'numerator': self.meta['grain']['duration'].numerator,
                                              'denominator': self.meta['grain']['duration'].denominator}

    def __len__(self) -> int:
        return 2

    @overload
    def __getitem__(self, index: int) -> "Union[GRAIN.MetadataDict, Optional[GRAIN.DataType]]": ...

    @overload  # noqa: F811
    def __getitem__(self, index: slice) -> """Union[Tuple[GRAIN.MetadataDict],
                                                    Tuple[GRAIN.MetadataDict, Optional[GRAIN.DataType]],
                                                    Tuple[Optional[GRAIN.DataType]],
                                                    Tuple[()]]""": ...

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

    @property
    def data(self) -> "Optional[GRAIN.DataType]":
        return self._data

    @data.setter
    def data(self, value: "Optional[GRAIN.DataType]"):
        self._data = value

    @property
    def grain_type(self) -> str:
        return self.meta['grain']['grain_type']

    @grain_type.setter
    def grain_type(self, value: str) -> None:
        self.meta['grain']['grain_type'] = value

    @property
    def source_id(self) -> UUID:
        return UUID(self.meta['grain']['source_id'])

    @source_id.setter
    def source_id(self, value: Union[UUID, str]) -> None:
        self.meta['grain']['source_id'] = str(value)

    @property
    def flow_id(self) -> UUID:
        return UUID(self.meta['grain']['flow_id'])

    @flow_id.setter
    def flow_id(self, value: Union[UUID, str]) -> None:
        self.meta['grain']['flow_id'] = str(value)

    @property
    def origin_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['origin_timestamp'])

    @origin_timestamp.setter
    def origin_timestamp(self, value: Union[TimeOffset, str]):
        if isinstance(value, TimeOffset):
            value = value.to_sec_nsec()
        self.meta['grain']['origin_timestamp'] = value

    def final_origin_timestamp(self) -> Timestamp:
        return self.origin_timestamp

    def origin_timerange(self) -> TimeRange:
        return TimeRange(self.origin_timestamp, self.final_origin_timestamp(), TimeRange.INCLUSIVE)

    def normalise_time(self, value: Timestamp) -> Timestamp:
        return value

    @property
    def sync_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['sync_timestamp'])

    @sync_timestamp.setter
    def sync_timestamp(self, value: Union[TimeOffset, str]) -> None:
        if isinstance(value, TimeOffset):
            value = value.to_sec_nsec()
        self.meta['grain']['sync_timestamp'] = value

    @property
    def creation_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['creation_timestamp'])

    @creation_timestamp.setter
    def creation_timestamp(self, value: Union[TimeOffset, str]) -> None:
        if isinstance(value, TimeOffset):
            value = value.to_sec_nsec()
        self.meta['grain']['creation_timestamp'] = value

    @property
    def rate(self) -> Fraction:
        return Fraction(self.meta['grain']['rate']['numerator'],
                        self.meta['grain']['rate']['denominator'])

    @rate.setter
    def rate(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['rate'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def duration(self) -> Fraction:
        return Fraction(self.meta['grain']['duration']['numerator'],
                        self.meta['grain']['duration']['denominator'])

    @duration.setter
    def duration(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['duration'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def timelabels(self) -> "GRAIN.TIMELABELS":
        return GRAIN.TIMELABELS(self)

    @timelabels.setter
    def timelabels(self, value: "Union[List[GRAIN.TIMELABEL], GRAIN.TIMELABELS]") -> None:
        self.meta['grain']['timelabels'] = []
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
        MetadataDict = Dict[str, Any]

        def __init__(self, meta: "Optional[GRAIN.TIMELABEL.MetadataDict]" = None):
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
        def __setitem__(self, key: int, value: "GRAIN.TIMELABEL.MetadataDict") -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: "Iterable[GRAIN.TIMELABEL.MetadataDict]") -> None: ...

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

        def insert(self, key: int, value: "GRAIN.TIMELABEL.MetadataDict") -> None:
            if 'timelabels' not in self.parent.meta['grain']:
                self.parent.meta['grain']['timelabels'] = []
            self.parent.meta['grain']['timelabels'].insert(key, dict(GRAIN.TIMELABEL(value)))

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
        else:
            return 0

    @property
    def expected_length(self) -> int:
        if 'length' in self.meta['grain']:
            return self.meta['grain']['length']
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
    def __init__(self, meta: GRAIN.MetadataDict, data: Optional[GRAIN.DataType]):
        super(EVENTGRAIN, self).__init__(meta, None)
        self._factory = "EventGrain"
        self.meta['grain']['grain_type'] = 'event'
        if 'event_payload' not in self.meta['grain']:
            self.meta['grain']['event_payload'] = {}
        if data is not None:
            if isinstance(data, bytes):
                self.data = data
            else:
                self.data = bytes(data)
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
            d = {'path': datum['path']}
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
        self.meta['grain']['event_payload']['data'] = [dict(datum) for datum in value]

    def append(self, path: str, pre: Optional[MediaJSONSerialisable] = None, post: Optional[MediaJSONSerialisable] = None) -> None:
        datum = {'path': path}
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

    ComponentDict = TypedDict('ComponentDict', {'stride': int, 'offset': int, 'width': int, 'height': int, 'length': int})

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
        def __init__(self, meta: "VIDEOGRAIN.ComponentDict"):
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
        def __setitem__(self, key: int, value: "VIDEOGRAIN.ComponentDict") -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: "Iterable[VIDEOGRAIN.ComponentDict]") -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if isinstance(key, int):
                self.parent.meta['grain']['cog_frame']['components'][key] = type(self.parent).COMPONENT(value)
            else:
                values = iter(value)
                for n in range(len(self))[key]:
                    self.parent.meta['grain']['cog_frame']['components'][n] = type(self.parent).COMPONENT(next(values))

        def __delitem__(self, key: Union[int, slice]) -> None:
            del self.parent.meta['grain']['cog_frame']['components'][key]

        def insert(self, key: int, value: "VIDEOGRAIN.ComponentDict") -> None:
            self.parent.meta['grain']['cog_frame']['components'].insert(key, type(self.parent).COMPONENT(value))

        def __len__(self) -> int:
            return len(self.parent.meta['grain']['cog_frame']['components'])

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

    def __init__(self, meta: GRAIN.MetadataDict, data: Optional[GRAIN.DataType]):
        super(VIDEOGRAIN, self).__init__(meta, data)
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

    def normalise_time(self, value: Timestamp) -> Timestamp:
        if self.rate == 0:
            return value
        return value.normalise(self.rate.numerator, self.rate.denominator)

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
            return Fraction(self.meta['grain']['cog_frame']['source_aspect_ratio']['numerator'],
                            self.meta['grain']['cog_frame']['source_aspect_ratio']['denominator'])
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
            return Fraction(self.meta['grain']['cog_frame']['pixel_aspect_ratio']['numerator'],
                            self.meta['grain']['cog_frame']['pixel_aspect_ratio']['denominator'])
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
    def __init__(self, meta: GRAIN.MetadataDict, data: GRAIN.DataType):
        super(CODEDVIDEOGRAIN, self).__init__(meta, data)
        self._factory = "CodedVideoGrain"
        self.meta['grain']['grain_type'] = 'coded_video'
        if 'cog_coded_frame' not in self.meta['grain']:
            self.meta['grain']['cog_coded_frame'] = {}
        if 'format' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['format'] = int(CogFrameFormat.UNKNOWN)
        if 'layout' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['layout'] = int(CogFrameLayout.UNKNOWN)
        for key in ['origin_width', 'origin_height', 'coded_width', 'coded_height', 'temporal_offset', 'length']:
            if key not in self.meta['grain']['cog_coded_frame']:
                self.meta['grain']['cog_coded_frame'][key] = 0
        if 'is_key_frame' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['is_key_frame'] = False
        self.meta['grain']['cog_coded_frame']['format'] = int(self.meta['grain']['cog_coded_frame']['format'])
        self.meta['grain']['cog_coded_frame']['layout'] = int(self.meta['grain']['cog_coded_frame']['layout'])

    def normalise_time(self, value: Timestamp) -> Timestamp:
        if self.rate == 0:
            return value
        return value.normalise(self.rate.numerator, self.rate.denominator)

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
                del self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key]
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
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'].insert(key, value)

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
            self.meta['grain']['cog_coded_frame']['unit_offsets'] = value
        elif 'unit_offsets' in self.meta['grain']['cog_coded_frame']:
            del self.meta['grain']['cog_coded_frame']['unit_offsets']


def size_for_audio_format(cog_audio_format, channels, samples):
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
    def __init__(self, meta, data):
        super(AUDIOGRAIN, self).__init__(meta, data)
        self._factory = "AudioGrain"
        self.meta['grain']['grain_type'] = 'audio'
        if 'cog_audio' not in self.meta['grain']:
            self.meta['grain']['cog_audio'] = {}
        if 'format' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['format'] = int(CogAudioFormat.INVALID)
        for key in ['samples', 'channels', 'sample_rate']:
            if key not in self.meta['grain']['cog_audio']:
                self.meta['grain']['cog_audio'][key] = 0
        self.meta['grain']['cog_audio']['format'] = int(self.meta['grain']['cog_audio']['format'])

    def final_origin_timestamp(self):
        return (self.origin_timestamp + TimeOffset.from_count(self.samples - 1, self.sample_rate, 1))

    def normalise_time(self, value):
        return value.normalise(self.sample_rate, 1)

    @property
    def format(self):
        return CogAudioFormat(self.meta['grain']['cog_audio']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_audio']['format'] = int(value)

    @property
    def samples(self):
        return self.meta['grain']['cog_audio']['samples']

    @samples.setter
    def samples(self, value):
        self.meta['grain']['cog_audio']['samples'] = int(value)

    @property
    def channels(self):
        return self.meta['grain']['cog_audio']['channels']

    @channels.setter
    def channels(self, value):
        self.meta['grain']['cog_audio']['channels'] = int(value)

    @property
    def sample_rate(self):
        return self.meta['grain']['cog_audio']['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value):
        self.meta['grain']['cog_audio']['sample_rate'] = int(value)

    @property
    def expected_length(self):
        return size_for_audio_format(self.format, self.channels, self.samples)


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
    def __init__(self, meta, data):
        super(CODEDAUDIOGRAIN, self).__init__(meta, data)
        self._factory = "CodedAudioGrain"
        self.meta['grain']['grain_type'] = 'coded_audio'
        if 'cog_coded_audio' not in self.meta['grain']:
            self.meta['grain']['cog_coded_audio'] = {}
        if 'format' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['format'] = int(CogAudioFormat.INVALID)
        for (key, DEF) in [('channels', 0),
                           ('samples', 0),
                           ('priming', 0),
                           ('remainder', 0),
                           ('sample_rate', 48000)]:
            if key not in self.meta['grain']['cog_coded_audio']:
                self.meta['grain']['cog_coded_audio'][key] = DEF
        self.meta['grain']['cog_coded_audio']['format'] = int(self.meta['grain']['cog_coded_audio']['format'])

    def final_origin_timestamp(self):
        return (self.origin_timestamp + TimeOffset.from_count(self.samples - 1, self.sample_rate, 1))

    def normalise_time(self, value):
        return value.normalise(self.sample_rate, 1)

    @property
    def format(self):
        return CogAudioFormat(self.meta['grain']['cog_coded_audio']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_coded_audio']['format'] = int(value)

    @property
    def channels(self):
        return self.meta['grain']['cog_coded_audio']['channels']

    @channels.setter
    def channels(self, value):
        self.meta['grain']['cog_coded_audio']['channels'] = value

    @property
    def samples(self):
        return self.meta['grain']['cog_coded_audio']['samples']

    @samples.setter
    def samples(self, value):
        self.meta['grain']['cog_coded_audio']['samples'] = value

    @property
    def priming(self):
        return self.meta['grain']['cog_coded_audio']['priming']

    @priming.setter
    def priming(self, value):
        self.meta['grain']['cog_coded_audio']['priming'] = value

    @property
    def remainder(self):
        return self.meta['grain']['cog_coded_audio']['remainder']

    @remainder.setter
    def remainder(self, value):
        self.meta['grain']['cog_coded_audio']['remainder'] = value

    @property
    def sample_rate(self):
        return self.meta['grain']['cog_coded_audio']['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value):
        self.meta['grain']['cog_coded_audio']['sample_rate'] = value


if __name__ == "__main__":  # pragma: no cover
    from uuid import uuid1, uuid5
    from .grain_constructors import Grain

    src_id = uuid1()
    flow_id = uuid5(src_id, "flow_id:test_flow")

    grain1 = Grain(src_id, flow_id)
    grain2 = Grain(grain1.meta)
    print(grain1)
    print(grain2)
