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

from __future__ import print_function
from __future__ import absolute_import

from six import string_types

from uuid import UUID
from nmoscommon.timestamp import Timestamp
from collections import Sequence, MutableSequence, Mapping
from fractions import Fraction

from .cogframe import CogFrameFormat, CogFrameLayout, CogAudioFormat

import json

__all__ = ["Grain", "VideoGrain", "AudioGrain", "CodedVideoGrain", "CodedAudioGrain", "EventGrain"]


class GRAIN(Sequence):
    """\
    A class representing a generic media grain.

    Any grain can be freely cast to a tuple:

      (meta, data)

    where meta is a dictionary containing the grain metadata, and data is a python buffer object representing the payload (or None for an empty grain).
    """
    def __init__(self, meta, data):
        self.meta = meta
        self.data = data
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
            return "{}({!r},{!r})".format(self._factory, self.meta, self.data)

    def __eq__(self, other):
        return tuple(self) == other

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
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
        self.meta['grain']['origin_timestamp'] = value

    @property
    def sync_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['sync_timestamp'])

    @sync_timestamp.setter
    def sync_timestamp(self, value):
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
        self.meta['grain']['sync_timestamp'] = value

    @property
    def creation_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['creation_timestamp'])

    @creation_timestamp.setter
    def creation_timestamp(self, value):
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
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
        if 'timelabels' in self.meta['grain']:
            return self.meta['grain']['timelabels']
        else:
            return []

    @property
    def length(self):
        return len(self.data)


class EVENTGRAIN(GRAIN):
    def __init__(self, meta, data):
        if data is not None:
            meta['grain']['event_payload'] = json.loads(data)
        super(EVENTGRAIN, self).__init__(meta, None)
        self._factory = "EventGrain"
        self.meta['grain']['grain_type'] = 'event'
        if 'event_payload' not in self.meta['grain']:
            self.meta['grain']['event_payload'] = {}
        if 'type' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['type'] = ""
        if 'topic' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['topic'] = ""
        if 'data' not in self.meta['grain']['event_payload']:
            self.meta['grain']['event_payload']['data'] = []

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
        datum = { 'path' : path }
        if pre is not None:
            datum['pre'] = pre
        if post is not None:
            datum['post'] = post
        self.meta['grain']['event_payload']['data'].append(datum)


class VIDEOGRAIN(GRAIN):

    class COMPONENT(Mapping):
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

        def __getitem__(self,key):
            return VIDEOGRAIN.COMPONENT(self.parent.meta['grain']['cog_frame']['components'][key])

        def __setitem__(self,key,value):
            self.parent.meta['grain']['cog_frame']['components'][key] = VIDEOGRAIN.COMPONENT(value)

        def __delitem__(self,key):
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
                'format': CogFrameFormat.UNKNOWN,
                'width': 0,
                'height': 0,
                'layout': CogFrameLayout.UNKNOWN,
                'extension': 0,
                'components': []
            }
        if not isinstance(self.meta['grain']['cog_frame']['format'], CogFrameFormat):
            self.meta['grain']['cog_frame']['format'] = CogFrameFormat(self.meta['grain']['cog_frame']['format'])
        if not isinstance(self.meta['grain']['cog_frame']['layout'], CogFrameLayout):
            self.meta['grain']['cog_frame']['layout'] = CogFrameLayout(self.meta['grain']['cog_frame']['layout'])
        self.components = VIDEOGRAIN.COMPONENT_LIST(self)

    @property
    def format(self):
        return self.meta['grain']['cog_frame']['format']

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_frame']['format'] = CogFrameFormat(value)

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
        return self.meta['grain']['cog_frame']['layout']

    @layout.setter
    def layout(self, value):
        self.meta['grain']['cog_frame']['layout'] = CogFrameLayout(value)

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
        self.meta['grain']['cog_frame']['source_aspect_ratio'] = { 'numerator': value.numerator,
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
        self.meta['grain']['cog_frame']['pixel_aspect_ratio'] = { 'numerator': value.numerator,
                                                         'denominator': value.denominator}


class CODEDVIDEOGRAIN(GRAIN):
    def __init__(self, meta, data):
        super(CODEDVIDEOGRAIN, self).__init__(meta, data)
        self._factory = "CodedVideoGrain"
        self.meta['grain']['grain_type'] = 'coded_video'
        if 'cog_coded_frame' not in self.meta['grain']:
            self.meta['grain']['cog_coded_frame'] = {}
        if 'format' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['format'] = CogFrameFormat.UNKNOWN
        if 'layout' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['layout'] = CogFrameLayout.UNKNOWN
        for key in ['origin_width', 'origin_height', 'coded_width', 'coded_height', 'temportal_offset', 'length' ]:
            if key not in self.meta['grain']['cog_coded_frame']:
                self.meta['grain']['cog_coded_frame'][key] = 0
        if 'is_key_frame' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['is_key_frame'] = False
        if not isinstance(self.meta['grain']['cog_coded_frame']['format'], CogFrameFormat):
            self.meta['grain']['cog_coded_frame']['format'] = CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])
        if not isinstance(self.meta['grain']['cog_coded_frame']['layout'], CogFrameLayout):
            self.meta['grain']['cog_coded_frame']['layout'] = CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @property
    def format(self):
        return CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_coded_frame']['format'] = CogFrameFormat(value)

    @property
    def layout(self):
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @layout.setter
    def layout(self, value):
        self.meta['grain']['cog_coded_frame']['layout'] = CogFrameLayout(value)

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


class AUDIOGRAIN(GRAIN):
    def __init__(self, meta, data):
        super(AUDIOGRAIN, self).__init__(meta, data)
        self._factory = "AudioGrain"
        self.meta['grain']['grain_type'] = 'audio'
        if 'cog_audio' not in self.meta['grain']:
            self.meta['grain']['cog_audio'] = {}
        if 'format' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['format'] = CogAudioFormat.INVALID
        for key in ['samples', 'channels', 'sample_rate']:
            if key not in self.meta['grain']['cog_audio']:
                self.meta['grain']['cog_audio'][key] = 0

    @property
    def format(self):
        return CogAudioFormat(self.meta['grain']['cog_audio']['format'])

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_audio']['format'] = CogAudioFormat(value)

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


class CODEDAUDIOGRAIN(GRAIN):
    def __init__(self, meta, data):
        super(CODEDAUDIOGRAIN, self).__init__(meta, data)
        self._factory = "CodedAudioGrain"
        self.meta['grain']['grain_type'] = 'coded_audio'
        if 'cog_coded_audio' not in self.meta['grain']:
            self.meta['grain']['cog_coded_audio'] = {}
        if 'format' not in self.meta['grain']['cog_coded_audio']:
            self.meta['grain']['cog_coded_audio']['format'] = CogAudioFormat.INVALID
        for (key, DEF) in [('channels', 0),
                           ('samples', 0),
                           ('priming', 0),
                           ('remainder', 0),
                           ('sample_rate', 48000)]:
            if key not in self.meta['grain']['cog_coded_audio']:
                self.meta['grain']['cog_coded_audio'][key] = DEF
        if not isinstance(self.meta['grain']['cog_coded_audio']['format'], CogAudioFormat):
            self.meta['grain']['cog_coded_audio']['format'] = CogAudioFormat(self.meta['grain']['cog_coded_audio']['format'])
        
    @property
    def format(self):
        return self.meta['grain']['cog_coded_audio']['format']

    @format.setter
    def format(self, value):
        self.meta['grain']['cog_coded_audio']['format'] = CogAudioFormat(value)

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


def size_for_format(fmt, w, h):
    if ((fmt >> 8) & 0x1) == 0x00:  # Cog frame is not packed
        h_shift = (fmt & 0x01)
        v_shift = ((fmt >> 1) & 0x01)
        depth = (fmt & 0xc)
        if depth == 0:
            bpv = 1
        elif depth == 4:
            bpv = 2
        else:
            bpv = 4

        return (w*h + 2*((w*h) >> (h_shift + v_shift)))*bpv
    else:
        if fmt in (CogFrameFormat.YUYV,
                   CogFrameFormat.UYVY,
                   CogFrameFormat.AYUV):
            return w*h*2
        elif fmt in (CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ARGB,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRA,
                     CogFrameFormat.xBGR,
                     CogFrameFormat.ABGR):
            return w*h*4
        elif fmt == CogFrameFormat.RGB:
            return w*h*3
        elif fmt == CogFrameFormat.v210:
            return h*(((w + 47) // 48) * 128)
        elif fmt == CogFrameFormat.v216:
            return w*h*4
        else:
            return 0

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

def components_for_format(fmt, w, h):
    components = []
    if ((fmt>>8)&0x1) == 0x00:  # Cog frame is not packed
        h_shift = (fmt&0x01)
        v_shift = ((fmt>>1)&0x01)
        depth = (fmt&0xc)
        if depth == 0:
            bpv = 1
        elif depth == 4:
            bpv = 2
        else:
            bpv = 4

        offset = 0
        components.append({
            'stride': w*bpv,
            'offset': offset,
            'width': w,
            'height': h,
            'length': w*h*bpv
        })
        offset += w*h*bpv

        components.append({
            'stride': (w >> h_shift)*bpv,
            'offset': offset,
            'width': w >> h_shift,
            'height': h >> v_shift,
            'length': ((w*h) >> (h_shift + v_shift))*bpv
        })
        offset += ((w*h) >> (h_shift + v_shift))*bpv

        components.append({
            'stride': (w >> h_shift)*bpv,
            'offset': offset,
            'width': w >> h_shift,
            'height': h >> v_shift,
            'length': ((w*h) >> (h_shift + v_shift))*bpv
        })
        offset += ((w*h) >> (h_shift + v_shift))*bpv

    else:
        if fmt in (CogFrameFormat.YUYV,
                   CogFrameFormat.UYVY,
                   CogFrameFormat.AYUV):
            components.append({
                'stride': w*2,
                'offset': 0,
                'width': w,
                'height': h,
                'length': h*w*2
            })
        elif fmt in (CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ARGB,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRA,
                     CogFrameFormat.xBGR,
                     CogFrameFormat.ABGR):
            components.append({
                'stride': w*4,
                'offset': 0,
                'width': w,
                'height': h,
                'length': h*w*4
            })
        elif fmt == CogFrameFormat.RGB:
            components.append({
                'stride': w*3,
                'offset': 0,
                'width': w,
                'height': h,
                'length': h*w*3
            })
        elif fmt == CogFrameFormat.v210:
            components.append({
                'stride': (((w + 47) // 48) * 128),
                'offset': 0,
                'width': w,
                'height': h,
                'length': h*(((w + 47) // 48) * 128)
            })
        elif fmt == CogFrameFormat.v216:
            components.append({
                'stride': w*4,
                'offset': 0,
                'width': w,
                'height': h,
                'length': h*w*4
            })
    return components


def AudioGrain(src_id_or_meta, flow_id_or_data=None, origin_timestamp=None,
               sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
               cog_audio_format=CogAudioFormat.INVALID,
               samples=0,
               channels=0,
               sample_rate=48000,
               flow_id=None, data=None):
    meta = None
    src_id = None

    if isinstance(src_id_or_meta, dict):
        meta = src_id_or_meta
        if data is None:
            data = flow_id_or_data
    else:
        src_id = src_id_or_meta
        if flow_id is None:
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(origin_timestamp),
                "sync_timestamp": str(sync_timestamp),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "cog_audio": {
                    "format": cog_audio_format,
                    "samples": samples,
                    "channels": channels,
                    "sample_rate": sample_rate
                }
            }
        }

    if data is None:
        size = size_for_audio_format(cog_audio_format, channels, samples)
        data = bytearray(size)

    return AUDIOGRAIN(meta, data)


def CodedAudioGrain(src_id_or_meta, flow_id_or_data=None, origin_timestamp=None,
                    sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
                    cog_audio_format=CogAudioFormat.INVALID,
                    samples=0,
                    channels=0,
                    priming=0,
                    remainder=0,
                    sample_rate=48000,
                    length=None,
                    flow_id=None, data=None):
    meta = None
    src_id = None

    if isinstance(src_id_or_meta, dict):
        meta = src_id_or_meta
        if data is None:
            data = flow_id_or_data
    else:
        src_id = src_id_or_meta
        if flow_id is None:
            flow_id = flow_id_or_data

    if length is None:
        if data is not None:
            length = len(data)
        else:
            length = 0

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_audio",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(origin_timestamp),
                "sync_timestamp": str(sync_timestamp),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "cog_coded_audio": {
                    "format": cog_audio_format,
                    "samples": samples,
                    "channels": channels,
                    "priming": priming,
                    "remainder": remainder,
                    "sample_rate": sample_rate
                }
            }
        }

    if data is None:
        data = bytearray(length)

    return CODEDAUDIOGRAIN(meta, data)


def VideoGrain(src_id_or_meta, flow_id_or_data=None, origin_timestamp=None,
               sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
               cog_frame_format=CogFrameFormat.UNKNOWN, width=1920,
               height=1080, cog_frame_layout=CogFrameLayout.UNKNOWN,
               flow_id=None, data=None):
    meta = None
    src_id = None

    if isinstance(src_id_or_meta, dict):
        meta = src_id_or_meta
        if data is None:
            data = flow_id_or_data
    else:
        src_id = src_id_or_meta
        if flow_id is None:
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "video",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(origin_timestamp),
                "sync_timestamp": str(sync_timestamp),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "cog_frame": {
                    "format": cog_frame_format,
                    "width": width,
                    "height": height,
                    "layout": cog_frame_layout,
                    "extension": 0,
                    "components": []
                }
            },
        }

    if data is None:
        size = size_for_format(cog_frame_format, width, height)
        data = bytearray(size)

    if "cog_frame" in meta['grain'] and ("components" not in meta['grain']['cog_frame'] or len(meta['grain']['cog_frame']['components']) == 0):
        meta['grain']['cog_frame']['components'] = components_for_format(cog_frame_format, width, height)

    return VIDEOGRAIN(meta, data)

def CodedVideoGrain(src_id_or_meta, flow_id_or_data=None, origin_timestamp=None,
                    sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
                    cog_frame_format=CogFrameFormat.UNKNOWN, origin_width=1920,
                    origin_height=1080, coded_width=None,
                    coded_height=None, temporal_offset=0, length=None,
                    cog_frame_layout=CogFrameLayout.UNKNOWN, unit_offsets=None,
                    flow_id=None, data=None):
    meta = None
    src_id = None

    if isinstance(src_id_or_meta, dict):
        meta = src_id_or_meta
        if data is None:
            data = flow_id_or_data
    else:
        src_id = src_id_or_meta
        if flow_id is None:
            flow_id = flow_id_or_data

    if coded_width is None:
        coded_width = origin_width
    if coded_height is None:
        coded_height = origin_height

    if length is None:
        if data is not None:
            length = len(data)
        else:
            length = 0

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_video",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(origin_timestamp),
                "sync_timestamp": str(sync_timestamp),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "cog_coded_frame": {
                    "format": cog_frame_format,
                    "origin_width": origin_width,
                    "origin_height": origin_height,
                    "coded_width": coded_width,
                    "coded_height": coded_height,
                    "layout": cog_frame_layout,
                    "temporal_offset": temporal_offset
                }
            },
        }

    if data is None:
        data = bytearray(length)

    if "grain" in meta and "cog_coded_frame" in meta['grain'] and unit_offsets is not None:
        meta['grain']['cog_coded_frame']['unit_offsets'] = unit_offsets

    return CODEDVIDEOGRAIN(meta, data)


def EventGrain(src_id_or_meta, flow_id_or_data=None, origin_timestamp=None,
               sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
               event_type='', topic='',
               flow_id=None, data=None):
    meta = None
    src_id = None

    if isinstance(src_id_or_meta, dict):
        meta = src_id_or_meta
        if data is None:
            data = flow_id_or_data
    else:
        src_id = src_id_or_meta
        if flow_id is None:
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "event",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(origin_timestamp),
                "sync_timestamp": str(sync_timestamp),
                "creation_timestamp": str(cts),
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
        }

    return EVENTGRAIN(meta, data)

def Grain(src_id_or_meta=None, flow_id_or_data=None, origin_timestamp=None,
          sync_timestamp=None, rate=Fraction(25,1), duration=Fraction(1,25),
          flow_id=None, data=None, src_id=None, meta=None):
    """\
    Several possible ways to construct a grain:

      Grain(src_id, flow_id, origin_timestamp=current_time,
            sync_timestamp=origin_timestamp)

    creates a new empty grain in the specified source id (uuid.UUID or string)
    and flow_id

      Grain(meta, [ data ])

    creates a new grain with the specified data and optional buffer object
    for payload
"""

    if meta is None:
        if isinstance(src_id_or_meta, dict):
            meta = src_id_or_meta
            if data is None:
                data = flow_id_or_data
        else:
            src_id = src_id_or_meta
            if flow_id is None:
                flow_id = flow_id_or_data

    if meta is None:
        cts = Timestamp.get_time()
        ots = origin_timestamp
        sts = sync_timestamp

        if ots is None:
            ots = cts
        if sts is None:
            sts = ots

        if src_id is None or flow_id is None:
            raise AttributeError("Must specify at least meta or src_id and flow_id")

        if isinstance(src_id, UUID):
            src_id = str(src_id)
        if isinstance(flow_id, UUID):
            flow_id = str(flow_id)

        if not isinstance(src_id, string_types) or not isinstance(flow_id, string_types):
            raise AttributeError("Invalid types for src_id and flow_id")

        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "empty",
                "source_id": src_id,
                "flow_id": flow_id,
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 0,
                    "denominator": 1,
                    },
                "duration": {
                    "numerator": 0,
                    "denominator": 1,
                    },
                }
            }
        data = None

    if 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'video':
        return VideoGrain(meta, data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'audio':
        return AudioGrain(meta, data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'coded_video':
        return CodedVideoGrain(meta, data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'coded_audio':
        return CodedAudioGrain(meta, data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] in ['event', 'data']:
        return EventGrain(meta, data)
    else:
        return GRAIN(meta, data)


if __name__ == "__main__":  # pragma: no cover
    from uuid import uuid1, uuid5

    src_id = uuid1()
    flow_id = uuid5(src_id, "flow_id:test_flow")

    grain1 = Grain(src_id, flow_id)
    grain2 = Grain(grain1.meta)
    print(grain1)
    print(grain2)
