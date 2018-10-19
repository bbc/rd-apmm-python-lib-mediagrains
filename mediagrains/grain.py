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

from __future__ import print_function
from __future__ import absolute_import

from six import string_types

from uuid import UUID
from mediatimestamp import Timestamp, TimeOffset
from collections import Sequence, MutableSequence, Mapping
from fractions import Fraction
from copy import copy, deepcopy

from .cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat

import json

__all__ = ["GRAIN", "VIDEOGRAIN", "AUDIOGRAIN", "CODEDVIDEOGRAIN", "CODEDAUDIOGRAIN", "EVENTGRAIN"]


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
    The data bytes-like object, or None

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


In addition there is a method provided for convenience:


final_origin_timestamp()
    The origin timestamp of the final sample in the grain. For most grain types this is the same as
    origin_timestamp, but not for audio grains.
    """
    def __init__(self, meta, data):
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

    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index == 0:
            return self.meta
        elif index == 1:
            return self.data
        else:
            raise IndexError("tuple index out of range")

    def __repr__(self):
        if self.data is None:
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< binary data of length {} >)".format(self._factory, self.meta, len(self.data))

    def __eq__(self, other):
        return tuple(self) == other

    def __copy__(self):
        from .grain_constructors import Grain
        return Grain(copy(self.meta), self.data)

    def __deepcopy__(self, memo):
        from .grain_constructors import Grain
        return Grain(deepcopy(self.meta), deepcopy(self.data))

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def grain_type(self):
        return self.meta['grain']['grain_type']

    @grain_type.setter
    def grain_type(self, value):
        self.meta['grain']['grain_type'] = value

    @property
    def source_id(self):
        return UUID(self.meta['grain']['source_id'])

    @source_id.setter
    def source_id(self, value):
        self.meta['grain']['source_id'] = str(value)

    @property
    def flow_id(self):
        return UUID(self.meta['grain']['flow_id'])

    @flow_id.setter
    def flow_id(self, value):
        self.meta['grain']['flow_id'] = str(value)

    @property
    def origin_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['origin_timestamp'])

    @origin_timestamp.setter
    def origin_timestamp(self, value):
        if isinstance(value, TimeOffset):
            if value.sign < 0:
                raise ValueError("Grain timestamps cannot be negative")
            value = value.to_sec_nsec()
        self.meta['grain']['origin_timestamp'] = value

    def final_origin_timestamp(self):
        return self.origin_timestamp

    @property
    def sync_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['sync_timestamp'])

    @sync_timestamp.setter
    def sync_timestamp(self, value):
        if isinstance(value, TimeOffset):
            if value.sign < 0:
                raise ValueError("Grain timestamps cannot be negative")
            value = value.to_sec_nsec()
        self.meta['grain']['sync_timestamp'] = value

    @property
    def creation_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['creation_timestamp'])

    @creation_timestamp.setter
    def creation_timestamp(self, value):
        if isinstance(value, TimeOffset):
            if value.sign < 0:
                raise ValueError("Grain timestamps cannot be negative")
            value = value.to_sec_nsec()
        self.meta['grain']['creation_timestamp'] = value

    @property
    def rate(self):
        return Fraction(self.meta['grain']['rate']['numerator'],
                        self.meta['grain']['rate']['denominator'])

    @rate.setter
    def rate(self, value):
        value = Fraction(value)
        self.meta['grain']['rate'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def duration(self):
        return Fraction(self.meta['grain']['duration']['numerator'],
                        self.meta['grain']['duration']['denominator'])

    @duration.setter
    def duration(self, value):
        value = Fraction(value)
        self.meta['grain']['duration'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def timelabels(self):
        return GRAIN.TIMELABELS(self)

    @timelabels.setter
    def timelabels(self, value):
        self.meta['grain']['timelabels'] = []
        for x in value:
            self.timelabels.append(x)

    def add_timelabel(self, tag, count, rate, drop_frame=False):
        tl = GRAIN.TIMELABEL()
        tl.tag = tag
        tl.count = count
        tl.rate = rate
        tl.drop_frame = drop_frame
        self.timelabels.append(tl)

    class TIMELABEL(Mapping):
        def __init__(self, meta=None):
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

        def __getitem__(self, key):
            return self.meta[key]

        def __setitem__(self, key, value):
            if key not in ['tag', 'timelabel']:
                raise KeyError
            self.meta[key] = value

        def __iter__(self):
            return self.meta.__iter__()

        def __len__(self):
            return 2

        def __eq__(self, other):
            return dict(self) == other

        @property
        def tag(self):
            return self.meta['tag']

        @tag.setter
        def tag(self, value):
            self.meta['tag'] = value

        @property
        def count(self):
            return self.meta['timelabel']['frames_since_midnight']

        @count.setter
        def count(self, value):
            self.meta['timelabel']['frames_since_midnight'] = int(value)

        @property
        def rate(self):
            return Fraction(self.meta['timelabel']['frame_rate_numerator'],
                            self.meta['timelabel']['frame_rate_denominator'])

        @rate.setter
        def rate(self, value):
            value = Fraction(value)
            self.meta['timelabel']['frame_rate_numerator'] = value.numerator
            self.meta['timelabel']['frame_rate_denominator'] = value.denominator

        @property
        def drop_frame(self):
            return self.meta['timelabel']['drop_frame']

        @drop_frame.setter
        def drop_frame(self, value):
            self.meta['timelabel']['drop_frame'] = bool(value)

    class TIMELABELS(MutableSequence):
        def __init__(self, parent):
            self.parent = parent

        def __getitem__(self, key):
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list index out of range")
            return GRAIN.TIMELABEL(self.parent.meta['grain']['timelabels'][key])

        def __setitem__(self, key, value):
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")
            self.parent.meta['grain']['timelabels'][key] = dict(GRAIN.TIMELABEL(value))

        def __delitem__(self, key):
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")
            del self.parent.meta['grain']['timelabels'][key]
            if len(self.parent.meta['grain']['timelabels']) == 0:
                del self.parent.meta['grain']['timelabels']

        def insert(self, key, value):
            if 'timelabels' not in self.parent.meta['grain']:
                self.parent.meta['grain']['timelabels'] = []
            self.parent.meta['grain']['timelabels'].insert(key, dict(GRAIN.TIMELABEL(value)))

        def __len__(self):
            if 'timelabels' not in self.parent.meta['grain']:
                return 0
            return len(self.parent.meta['grain']['timelabels'])

        def __eq__(self, other):
            return list(self) == other

    @property
    def length(self):
        if self.data is not None:
            return len(self.data)
        else:
            return 0

    @property
    def expected_length(self):
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
    The data bytes-like object, containing a json representation of the data

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
    def __init__(self, meta, data):
        super(EVENTGRAIN, self).__init__(meta, None)
        self._factory = "EventGrain"
        self.meta['grain']['grain_type'] = 'event'
        if 'event_payload' not in self.meta['grain']:
            self.meta['grain']['event_payload'] = {}
        if data is not None:
            self.data = data
        if 'type' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['type'] = ""
        if 'topic' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['topic'] = ""
        if 'data' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['data'] = []

    @property
    def data(self):
        return json.dumps({'type': self.event_type,
                           'topic': self.topic,
                           'data': [dict(datum) for datum in self.event_data]}).encode('utf-8')

    @data.setter
    def data(self, value):
        if not isinstance(value, string_types):
            value = value.decode('utf-8')
        value = json.loads(value)
        if 'type' not in value or 'topic' not in value or 'data' not in value:
            raise ValueError("incorrectly formated event payload")
        self.event_type = value['type']
        self.topic = value['topic']
        self.meta['grain']['event_payload']['data'] = []
        for datum in value['data']:
            d = {'path': datum['path']}
            if 'pre' in datum:
                d['pre'] = datum['pre']
            if 'post' in datum:
                d['post'] = datum['post']
            self.meta['grain']['event_payload']['data'].append(d)

    def __repr__(self):
        return "EventGrain({!r})".format(self.meta)

    @property
    def event_type(self):
        return self.meta['grain']['event_payload']['type']

    @event_type.setter
    def event_type(self, value):
        self.meta['grain']['event_payload']['type'] = value

    @property
    def topic(self):
        return self.meta['grain']['event_payload']['topic']

    @topic.setter
    def topic(self, value):
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
        def __init__(self, meta):
            self.meta = meta

        def __getitem__(self, key):
            return self.meta[key]

        def __setitem__(self, key, value):
            self.meta[key] = value

        def __delitem__(self, key):
            del self.meta[key]

        def __iter__(self):
            return self.meta.__iter__()

        def __len__(self):
            return self.meta.__len__()

        def __eq__(self, other):
            return dict(self) == other

        @property
        def path(self):
            return self.meta['path']

        @path.setter
        def path(self, value):
            self.meta['path'] = value

        @property
        def pre(self):
            if 'pre' in self.meta:
                return self.meta['pre']
            else:
                return None

        @pre.setter
        def pre(self, value):
            if value is not None:
                self.meta['pre'] = value
            else:
                del self.meta['pre']

        @property
        def post(self):
            if 'post' in self.meta:
                return self.meta['post']
            elif 'pre' in self.meta:
                return None

        @post.setter
        def post(self, value):
            if value is not None:
                self.meta['post'] = value
            elif 'post' in self.meta:
                del self.meta['post']

    @property
    def event_data(self):
        return [EVENTGRAIN.DATA(datum) for datum in self.meta['grain']['event_payload']['data']]

    @event_data.setter
    def event_data(self, value):
        self.meta['grain']['event_payload']['data'] = [dict(datum) for datum in value]

    def append(self, path, pre=None, post=None):
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

where meta is a dictionary containing the grain metadata, and data is a
bytes-like object containing the raw video data.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    The data bytes-like object, or None

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
        def __init__(self, meta):
            self.meta = meta

        def __getitem__(self, key):
            return self.meta[key]

        def __setitem__(self, key, value):
            self.meta[key] = value

        def __delitem__(self, key):
            del self.meta[key]

        def __iter__(self):
            return self.meta.__iter__()

        def __len__(self):
            return self.meta.__len__()

        def __eq__(self, other):
            return dict(self) == other

        @property
        def stride(self):
            return self.meta['stride']

        @stride.setter
        def stride(self, value):
            self.meta['stride'] = value

        @property
        def offset(self):
            return self.meta['offset']

        @offset.setter
        def offset(self, value):
            self.meta['offset'] = value

        @property
        def width(self):
            return self.meta['width']

        @width.setter
        def width(self, value):
            self.meta['width'] = value

        @property
        def height(self):
            return self.meta['height']

        @height.setter
        def height(self, value):
            self.meta['height'] = value

        @property
        def length(self):
            return self.meta['length']

        @length.setter
        def length(self, value):
            self.meta['length'] = value

    class COMPONENT_LIST(MutableSequence):
        def __init__(self, parent):
            self.parent = parent

        def __getitem__(self, key):
            return VIDEOGRAIN.COMPONENT(self.parent.meta['grain']['cog_frame']['components'][key])

        def __setitem__(self, key, value):
            self.parent.meta['grain']['cog_frame']['components'][key] = VIDEOGRAIN.COMPONENT(value)

        def __delitem__(self, key):
            del self.parent.meta['grain']['cog_frame']['components'][key]

        def insert(self, key, value):
            self.parent.meta['grain']['cog_frame']['components'].insert(key, VIDEOGRAIN.COMPONENT(value))

        def __len__(self):
            return len(self.parent.meta['grain']['cog_frame']['components'])

        def __eq__(self, other):
            return list(self) == other

    def __init__(self, meta, data):
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

    @property
    def format(self):
        return CogFrameFormat(self.meta['grain']['cog_frame']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_frame']['format'] = int(value)

    @property
    def width(self):
        return self.meta['grain']['cog_frame']['width']

    @width.setter
    def width(self, value):
        self.meta['grain']['cog_frame']['width'] = value

    @property
    def height(self):
        return self.meta['grain']['cog_frame']['height']

    @height.setter
    def height(self, value):
        self.meta['grain']['cog_frame']['height'] = value

    @property
    def layout(self):
        return CogFrameLayout(self.meta['grain']['cog_frame']['layout'])

    @layout.setter
    def layout(self, value):
        self.meta['grain']['cog_frame']['layout'] = int(value)

    @property
    def extension(self):
        return self.meta['grain']['cog_frame']['extension']

    @extension.setter
    def extension(self, value):
        self.meta['grain']['cog_frame']['extension'] = value

    @property
    def source_aspect_ratio(self):
        if 'source_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(self.meta['grain']['cog_frame']['source_aspect_ratio']['numerator'],
                            self.meta['grain']['cog_frame']['source_aspect_ratio']['denominator'])
        else:
            return None

    @source_aspect_ratio.setter
    def source_aspect_ratio(self, value):
        value = Fraction(value)
        self.meta['grain']['cog_frame']['source_aspect_ratio'] = {'numerator': value.numerator,
                                                                  'denominator': value.denominator}

    @property
    def pixel_aspect_ratio(self):
        if 'pixel_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(self.meta['grain']['cog_frame']['pixel_aspect_ratio']['numerator'],
                            self.meta['grain']['cog_frame']['pixel_aspect_ratio']['denominator'])
        else:
            return None

    @pixel_aspect_ratio.setter
    def pixel_aspect_ratio(self, value):
        value = Fraction(value)
        self.meta['grain']['cog_frame']['pixel_aspect_ratio'] = {'numerator': value.numerator,
                                                                 'denominator': value.denominator}

    @property
    def expected_length(self):
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

where meta is a dictionary containing the grain metadata, and data is a
bytes-like object containing the coded video data.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    The data bytes-like object, or None

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
    def __init__(self, meta, data):
        super(CODEDVIDEOGRAIN, self).__init__(meta, data)
        self._factory = "CodedVideoGrain"
        self.meta['grain']['grain_type'] = 'coded_video'
        if 'cog_coded_frame' not in self.meta['grain']:
            self.meta['grain']['cog_coded_frame'] = {}
        if 'format' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['format'] = int(CogFrameFormat.UNKNOWN)
        if 'layout' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['layout'] = int(CogFrameLayout.UNKNOWN)
        for key in ['origin_width', 'origin_height', 'coded_width', 'coded_height', 'temportal_offset', 'length']:
            if key not in self.meta['grain']['cog_coded_frame']:
                self.meta['grain']['cog_coded_frame'][key] = 0
        if 'is_key_frame' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['is_key_frame'] = False
        self.meta['grain']['cog_coded_frame']['format'] = int(self.meta['grain']['cog_coded_frame']['format'])
        self.meta['grain']['cog_coded_frame']['layout'] = int(self.meta['grain']['cog_coded_frame']['layout'])

    @property
    def format(self):
        return CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_coded_frame']['format'] = int(value)

    @property
    def layout(self):
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @layout.setter
    def layout(self, value):
        self.meta['grain']['cog_coded_frame']['layout'] = int(value)

    @property
    def origin_width(self):
        return self.meta['grain']['cog_coded_frame']['origin_width']

    @origin_width.setter
    def origin_width(self, value):
        self.meta['grain']['cog_coded_frame']['origin_width'] = value

    @property
    def origin_height(self):
        return self.meta['grain']['cog_coded_frame']['origin_height']

    @origin_height.setter
    def origin_height(self, value):
        self.meta['grain']['cog_coded_frame']['origin_height'] = value

    @property
    def coded_width(self):
        return self.meta['grain']['cog_coded_frame']['coded_width']

    @coded_width.setter
    def coded_width(self, value):
        self.meta['grain']['cog_coded_frame']['coded_width'] = value

    @property
    def coded_height(self):
        return self.meta['grain']['cog_coded_frame']['coded_height']

    @coded_height.setter
    def coded_height(self, value):
        self.meta['grain']['cog_coded_frame']['coded_height'] = value

    @property
    def is_key_frame(self):
        return self.meta['grain']['cog_coded_frame']['is_key_frame']

    @is_key_frame.setter
    def is_key_frame(self, value):
        self.meta['grain']['cog_coded_frame']['is_key_frame'] = bool(value)

    @property
    def temporal_offset(self):
        return self.meta['grain']['cog_coded_frame']['temporal_offset']

    @temporal_offset.setter
    def temporal_offset(self, value):
        self.meta['grain']['cog_coded_frame']['temporal_offset'] = value

    class UNITOFFSETS(MutableSequence):
        def __init__(self, parent):
            self.parent = parent

        def __getitem__(self, key):
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key]
            else:
                raise IndexError("list index out of range")

        def __setitem__(self, key, value):
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key] = value
            else:
                raise IndexError("list assignment index out of range")

        def __delitem__(self, key):
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                del self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key]
                if len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets']) == 0:
                    del self.parent.meta['grain']['cog_coded_frame']['unit_offsets']
            else:
                raise IndexError("list assignment index out of range")

        def insert(self, key, value):
            if 'unit_offsets' not in self.parent.meta['grain']['cog_coded_frame']:
                d = []
                d.insert(key, value)
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'] = d
            else:
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'].insert(key, value)

        def __len__(self):
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])
            else:
                return 0

        def __eq__(self, other):
            return list(self) == other

        def __repr__(self):
            return repr(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])

    @property
    def unit_offsets(self):
        return CODEDVIDEOGRAIN.UNITOFFSETS(self)

    @unit_offsets.setter
    def unit_offsets(self, value):
        if len(value) != 0:
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

where meta is a dictionary containing the grain metadata, and data is a
bytes-like object containing the raw audio data.

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    The data bytes-like object, or None

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
    The data bytes-like object, or None

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
