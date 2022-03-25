from collections.abc import Mapping
from fractions import Fraction
from inspect import isawaitable

from typing import (
    List,
    Union,
    SupportsBytes,
    Optional,
    cast,
    Iterator,
    Awaitable)
from typing_extensions import Literal
from uuid import UUID

from mediatimestamp.immutable import Timestamp, SupportsMediaTimestamp, mediatimestamp
from ..typing import (
    MediaJSONSerialisable,
    EventGrainDatumDict,
    GrainDataType,
    EventGrainMetadataDict,
    GrainDataParameterType)

from .Grain import Grain

import json


class EventGrain(Grain):
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
    def __init__(self,
                 meta: EventGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
                 src_id: Optional[UUID] = None,
                 flow_id: Optional[UUID] = None,
                 origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                 creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                 sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                 rate: Fraction = Fraction(25, 1),
                 duration: Fraction = Fraction(1, 25),
                 event_type: str = '',
                 topic: str = ''):

        if meta is None:
            if src_id is None:
                raise AttributeError("src_id is None. Meta is None so src_id must not be None.")
            if flow_id is None:
                raise AttributeError("flow_id is None. Meta is None so flow_id must not be None.")

            if not isinstance(src_id, UUID):
                raise AttributeError(f"src_id: Seen type {type(src_id)}, expected UUID.")
            if not isinstance(flow_id, UUID):
                raise AttributeError(f"flow_id: Seen type {type(flow_id)}, expected UUID.")

            cts = creation_timestamp
            if cts is None:
                cts = Timestamp.get_time()
            if origin_timestamp is None:
                origin_timestamp = cts
            if sync_timestamp is None:
                sync_timestamp = origin_timestamp
            meta = EventGrainMetadataDict({
                "@_ns": "urn:x-ipstudio:ns:0.1",
                "grain": {
                    "grain_type": "event",
                    "source_id": str(src_id),
                    "flow_id": str(flow_id),
                    "origin_timestamp": str(mediatimestamp(origin_timestamp)),
                    "sync_timestamp": str(mediatimestamp(sync_timestamp)),
                    "creation_timestamp": str(mediatimestamp(cts)),
                    "rate": {
                        "numerator": Fraction(rate).numerator,
                        "denominator": Fraction(rate).denominator,
                        },
                    "duration": {
                        "numerator": Fraction(duration).numerator,
                        "denominator": Fraction(duration).denominator,
                        },
                    "event_payload": {
                        "type": event_type,
                        "topic": topic,
                        "data": []
                    }
                },
            })

        super().__init__(meta, None)
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
    def event_data(self) -> List["EventGrain.DATA"]:
        return [EventGrain.DATA(datum) for datum in self.meta['grain']['event_payload']['data']]

    @event_data.setter
    def event_data(self, value: List[EventGrainDatumDict]) -> None:
        self.meta['grain']['event_payload']['data'] = [cast(EventGrainDatumDict, dict(datum)) for datum in value]

    def append(self, path: str, pre: Optional[MediaJSONSerialisable] = None,
               post: Optional[MediaJSONSerialisable] = None) -> None:
        datum = EventGrainDatumDict(path=path)
        if pre is not None:
            datum['pre'] = pre
        if post is not None:
            datum['post'] = post
        self.meta['grain']['event_payload']['data'].append(datum)
