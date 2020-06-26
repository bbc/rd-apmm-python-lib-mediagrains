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

from asynctest import TestCase
import uuid
from mediagrains import Grain, VideoGrain, AudioGrain, CodedVideoGrain, CodedAudioGrain, EventGrain
from mediagrains.cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat
from mediatimestamp.immutable import Timestamp, TimeOffset, TimeRange
from asynctest import mock
from fractions import Fraction
import json
from copy import copy, deepcopy


src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
cts = Timestamp.from_tai_sec_nsec("417798915:0")
ots = Timestamp.from_tai_sec_nsec("417798915:5")
sts = Timestamp.from_tai_sec_nsec("417798915:10")

VIDEOGRAIN_TEST_METADATA = {
    "@_ns": "urn:x-ipstudio:ns:0.1",
    "grain": {
        "grain_type": "video",
        "source_id": str(src_id),
        "flow_id": str(flow_id),
        "origin_timestamp": str(ots),
        "sync_timestamp": str(sts),
        "creation_timestamp": str(cts),
        "rate": {
            "numerator": 25,
            "denominator": 1,
        },
        "duration": {
            "numerator": 1,
            "denominator": 25,
        },
        "cog_frame": {
            "format": CogFrameFormat.S16_422_10BIT,
            "width": 1920,
            "height": 1080,
            "layout": CogFrameLayout.FULL_FRAME,
            "extension": 0,
            "components": [
                {
                    'stride': 4096,
                    'width': 1920,
                    'height': 1080,
                    'offset': 0,
                    'length': 4096*1080
                },
                {
                    'stride': 2048,
                    'width': 960,
                    'height': 1080,
                    'offset': 4096*1080,
                    'length': 2048*1080
                },
                {
                    'stride': 2048,
                    'width': 960,
                    'height': 1080,
                    'offset': 4096*1080 + 2048*1080,
                    'length': 2048*1080
                }
            ]
        }
    },
}


class ConvertsToTimestamp (object):
    def __init__(self, ts: Timestamp):
        self.ts = ts

    def __mediatimestamp__(self) -> Timestamp:
        return self.ts


class TestGrain (TestCase):
    def test_empty_grain_creation(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(cts))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertIsNone(grain.media_rate)
        self.assertEqual(grain.duration, Fraction(0, 1))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain, (grain.meta, grain.data))
        self.assertIsNone(grain.data)
        self.assertEqual(grain.length, 0)
        self.assertEqual(grain.expected_length, 0)

    def test_empty_grain_creation_with_missing_data(self):
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        meta = {}

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.creation_timestamp, cts)

    def test_empty_grain_creation_with_odd_data(self):
        meta = {
            "grain": {
                "source_id": src_id,
                "flow_id": flow_id,
                "origin_timestamp": ots,
                "sync_timestamp": sts,
                "creation_timestamp": cts,
                "rate": Fraction(25, 1),
                "duration": Fraction(1, 25),
                "length": 23
            }
        }

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.length, 0)
        self.assertEqual(grain.expected_length, 23)

    def test_empty_grain_creation_with_ots(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 1))
        self.assertEqual(grain.timelabels, [])

    def test_empty_grain_creation_with_convertable_ots(self):
        converts_to_ots = ConvertsToTimestamp(ots)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=converts_to_ots)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 1))
        self.assertEqual(grain.timelabels, [])

    def test_empty_grain_creation_with_ots_and_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 1))
        self.assertEqual(grain.timelabels, [])

    def test_empty_grain_castable_to_tuple(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts)

        self.assertEqual(len(grain), 2)
        self.assertIsInstance(grain[0], dict)
        self.assertIsNone(grain[1])

        with self.assertRaises(IndexError):
            grain[2]

        self.assertIsInstance(tuple(grain[0]), tuple)

    def test_empty_grain_with_meta(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "empty",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                    },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                    },
                "timelabels": [{
                    "tag": "timelabel1",
                    "timelabel": {
                        "frames_since_midnight": 0,
                        "frame_rate_numerator": 25,
                        "frame_rate_denominator": 1,
                        "drop_frame": False
                    }
                }]
            }
        }

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [
            {
                "tag": "timelabel1",
                "timelabel": {
                    "frames_since_midnight": 0,
                    "frame_rate_numerator": 25,
                    "frame_rate_denominator": 1,
                    "drop_frame": False
                }
            }
        ])
        self.assertEqual(repr(grain), "Grain({!r})".format(meta))

    def test_empty_grain_setters(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts)

        new_src_id = uuid.UUID("18d1a52e-0a67-11e8-ba57-776dc8ceabcb")
        new_flow_id = uuid.UUID("1ed4cfb4-0a67-11e8-b803-733e0764879a")
        new_cts = Timestamp.from_tai_sec_nsec("417798915:15")
        new_ots = Timestamp.from_tai_sec_nsec("417798915:20")
        new_sts = Timestamp.from_tai_sec_nsec("417798915:25")
        new_grain_type = "potato"
        converts_to_ots = ConvertsToTimestamp(ots)

        grain.grain_type = new_grain_type
        self.assertEqual(grain.grain_type, new_grain_type)

        grain.source_id = new_src_id
        self.assertEqual(grain.source_id, new_src_id)

        grain.flow_id = new_flow_id
        self.assertEqual(grain.flow_id, new_flow_id)

        grain.origin_timestamp = new_ots
        self.assertEqual(grain.origin_timestamp, new_ots)
        self.assertEqual(grain.final_origin_timestamp(), new_ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(new_ots))

        grain.sync_timestamp = new_sts
        self.assertEqual(grain.sync_timestamp, new_sts)

        grain.creation_timestamp = new_cts
        self.assertEqual(grain.creation_timestamp, new_cts)

        grain.origin_timestamp = converts_to_ots
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))

        grain.rate = 50
        self.assertEqual(grain.rate, Fraction(50, 1))

        grain.duration = 0.25
        self.assertEqual(grain.duration, Fraction(1, 4))

        grain.data = bytearray(10)
        self.assertEqual(len(grain.data), 10)
        self.assertEqual(grain.length, 10)

        self.assertEqual(grain.timelabels, [])
        grain.add_timelabel('test', 1, 25)
        self.assertEqual(len(grain.timelabels), 1)
        self.assertEqual(grain.timelabels[0].tag, 'test')
        self.assertEqual(grain.timelabels[0].count, 1)
        self.assertEqual(grain.timelabels[0].rate, Fraction(25, 1))
        self.assertFalse(grain.timelabels[0].drop_frame)

        grain.timelabels[0]['tag'] = 'potato'
        self.assertEqual(grain.timelabels[0].tag, 'potato')

        with self.assertRaises(KeyError):
            grain.timelabels[0]['potato'] = 3

        self.assertEqual(len(grain.timelabels[0]), 2)

        grain.timelabels[0] = {
            'tag': 'other_tag',
            'timelabel': {
                'frames_since_midnight': 7,
                'frame_rate_numerator': 30000,
                'frame_rate_denominator': 1001,
                'drop_frame': True
            }
        }
        self.assertEqual(len(grain.timelabels), 1)
        self.assertEqual(grain.timelabels[0].tag, 'other_tag')
        self.assertEqual(grain.timelabels[0].count, 7)
        self.assertEqual(grain.timelabels[0].rate, Fraction(30000, 1001))
        self.assertTrue(grain.timelabels[0].drop_frame)

        del grain.timelabels[0]

        self.assertEqual(len(grain.timelabels), 0)

        with self.assertRaises(IndexError):
            del grain.timelabels[0]

        with self.assertRaises(IndexError):
            grain.timelabels[0] = {
                'tag': 'other_tag',
                'timelabel': {
                    'frames_since_midnight': 7,
                    'frame_rate_numerator': 30000,
                    'frame_rate_denominator': 1001,
                    'drop_frame': True
                }
            }

    def test_video_grain_create_YUV422_10bit(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.media_rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.width, 1920)
        self.assertEqual(grain.height, 1080)
        self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
        self.assertEqual(grain.extension, 0)
        self.assertIsNone(grain.source_aspect_ratio)
        self.assertIsNone(grain.pixel_aspect_ratio)

        self.assertEqual(len(grain.components), 3)
        self.assertEqual(grain.components[0].stride, 1920*2)
        self.assertEqual(grain.components[0].width, 1920)
        self.assertEqual(grain.components[0].height, 1080)
        self.assertEqual(grain.components[0].offset, 0)
        self.assertEqual(grain.components[0].length, 1920*1080*2)
        self.assertEqual(len(grain.components[0]), 5)

        self.assertEqual(grain.components[1].stride, 1920)
        self.assertEqual(grain.components[1].width, 1920/2)
        self.assertEqual(grain.components[1].height, 1080)
        self.assertEqual(grain.components[1].offset, 1920*1080*2)
        self.assertEqual(grain.components[1].length, 1920*1080)
        self.assertEqual(len(grain.components[1]), 5)

        self.assertEqual(grain.components[2].stride, 1920)
        self.assertEqual(grain.components[2].width, 1920/2)
        self.assertEqual(grain.components[2].height, 1080)
        self.assertEqual(grain.components[2].offset, 1920*1080*2 + 1920*1080)
        self.assertEqual(grain.components[2].length, 1920*1080)
        self.assertEqual(len(grain.components[2]), 5)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), 1920*1080*2*2)

        self.assertEqual(repr(grain), "VideoGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

        self.assertEqual(grain.components, [{'stride': 1920*2,
                                             'width': 1920,
                                             'height': 1080,
                                             'offset': 0,
                                             'length': 1920*1080*2},
                                            {'stride': 1920,
                                             'width': 1920/2,
                                             'height': 1080,
                                             'offset': 1920*1080*2,
                                             'length': 1920*1080},
                                            {'stride': 1920,
                                             'width': 1920/2,
                                             'height': 1080,
                                             'offset': 1920*1080*3,
                                             'length': 1920*1080}])
        self.assertEqual(grain.expected_length, 1920*1080*4)

    def test_video_grain_create_sizes(self):
        for (fmt, complens) in [
                (CogFrameFormat.S32_444, (1920*1080*4, 1920*1080*4, 1920*1080*4)),
                (CogFrameFormat.S32_422, (1920*1080*4, 1920*1080*2, 1920*1080*2)),
                (CogFrameFormat.S32_420, (1920*1080*4, 1920*1080, 1920*1080)),
                (CogFrameFormat.S16_444_10BIT, (1920*1080*2, 1920*1080*2, 1920*1080*2)),
                (CogFrameFormat.S16_422_10BIT, (1920*1080*2, 1920*1080, 1920*1080)),
                (CogFrameFormat.S16_420_10BIT, (1920*1080*2, 1920*1080/2, 1920*1080/2)),
                (CogFrameFormat.U8_444, (1920*1080, 1920*1080, 1920*1080)),
                (CogFrameFormat.U8_422, (1920*1080, 1920*1080/2, 1920*1080/2)),
                (CogFrameFormat.U8_420, (1920*1080, 1920*1080/4, 1920*1080/4)),
                (CogFrameFormat.UYVY, (1920*1080*2,)),
                (CogFrameFormat.RGB, (1920*1080*3,)),
                (CogFrameFormat.RGBA, (1920*1080*4,)),
                (CogFrameFormat.v210, (40*128*1080,)),
                (CogFrameFormat.v216, (1920*1080*4,)),
                (CogFrameFormat.UNKNOWN, ()),
                ]:
            with mock.patch.object(Timestamp, "get_time", return_value=cts):
                grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                   cog_frame_format=fmt,
                                   width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

            self.assertEqual(len(grain.components), len(complens))
            offset = 0
            for (complen, comp) in zip(complens, grain.components):
                self.assertEqual(complen, comp.length)
                self.assertEqual(offset, comp.offset)
                offset += complen

            self.assertEqual(len(grain.data), offset)

    def test_video_component_setters(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.components[0].stride = 23
        self.assertEqual(grain.components[0].stride, 23)
        grain.components[0].width = 23
        self.assertEqual(grain.components[0].width, 23)
        grain.components[0].height = 23
        self.assertEqual(grain.components[0].height, 23)
        grain.components[0].offset = 23
        self.assertEqual(grain.components[0].offset, 23)
        grain.components[0].length = 23
        self.assertEqual(grain.components[0].length, 23)

        grain.components[0]['length'] = 17
        self.assertEqual(grain.components[0].length, 17)

        grain.components.append({'stride': 1920,
                                 'width': 1920,
                                 'height': 1080,
                                 'offset': 1920*1080*2*2,
                                 'length': 1920*1080})

        self.assertEqual(grain.components[3].stride, 1920)
        self.assertEqual(grain.components[3].width, 1920)
        self.assertEqual(grain.components[3].height, 1080)
        self.assertEqual(grain.components[3].offset, 1920*1080*2*2)
        self.assertEqual(grain.components[3].length, 1920*1080)

        self.assertEqual(len(grain.components), 4)
        del grain.components[3]
        self.assertEqual(len(grain.components), 3)

        grain.components[0] = {'stride': 1920,
                               'width': 1920,
                               'height': 1080,
                               'offset': 1920*1080*2*2,
                               'length': 1920*1080}

        self.assertEqual(grain.components[0].stride, 1920)
        self.assertEqual(grain.components[0].width, 1920)
        self.assertEqual(grain.components[0].height, 1080)
        self.assertEqual(grain.components[0].offset, 1920*1080*2*2)
        self.assertEqual(grain.components[0].length, 1920*1080)

    def test_video_grain_with_sparse_meta(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "video",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                    },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                    }
            },
        }

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(meta)

        self.assertEqual(grain.format, CogFrameFormat.UNKNOWN)
        self.assertEqual(grain.width, 0)
        self.assertEqual(grain.height, 0)
        self.assertEqual(grain.layout, CogFrameLayout.UNKNOWN)
        self.assertEqual(grain.extension, 0)
        self.assertEqual(len(grain.components), 0)

    def test_video_grain_with_numeric_identifiers(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=0x2805,
                               width=1920, height=1080,
                               cog_frame_layout=0)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.width, 1920)
        self.assertEqual(grain.height, 1080)
        self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
        self.assertEqual(grain.extension, 0)
        self.assertIsNone(grain.source_aspect_ratio)
        self.assertIsNone(grain.pixel_aspect_ratio)

        self.assertEqual(len(grain.components), 3)
        self.assertEqual(grain.components[0].stride, 1920*2)
        self.assertEqual(grain.components[0].width, 1920)
        self.assertEqual(grain.components[0].height, 1080)
        self.assertEqual(grain.components[0].offset, 0)
        self.assertEqual(grain.components[0].length, 1920*1080*2)

        self.assertEqual(grain.components[1].stride, 1920)
        self.assertEqual(grain.components[1].width, 1920/2)
        self.assertEqual(grain.components[1].height, 1080)
        self.assertEqual(grain.components[1].offset, 1920*1080*2)
        self.assertEqual(grain.components[1].length, 1920*1080)

        self.assertEqual(grain.components[2].stride, 1920)
        self.assertEqual(grain.components[2].width, 1920/2)
        self.assertEqual(grain.components[2].height, 1080)
        self.assertEqual(grain.components[2].offset, 1920*1080*2 + 1920*1080)
        self.assertEqual(grain.components[2].length, 1920*1080)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), 1920*1080*2*2)

        self.assertEqual(repr(grain), "VideoGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

        self.assertEqual(dict(grain.components[0]), {'stride': 1920*2,
                                                     'width': 1920,
                                                     'height': 1080,
                                                     'offset': 0,
                                                     'length': 1920*1080*2})

    def test_video_grain_setters(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.format = CogFrameFormat.S16_444
        self.assertEqual(grain.format, CogFrameFormat.S16_444)
        grain.format = 0x0207
        self.assertEqual(grain.format, CogFrameFormat.VC2)

        grain.width = 2
        self.assertEqual(grain.width, 2)

        grain.height = 13
        self.assertEqual(grain.height, 13)

        grain.layout = CogFrameLayout.SEPARATE_FIELDS
        self.assertEqual(grain.layout, CogFrameLayout.SEPARATE_FIELDS)
        grain.layout = 0x02
        self.assertEqual(grain.layout, CogFrameLayout.SINGLE_FIELD)

        grain.extension = 1
        self.assertEqual(grain.extension, 1)

        grain.source_aspect_ratio = 50
        self.assertEqual(grain.source_aspect_ratio, Fraction(50, 1))

        grain.pixel_aspect_ratio = 0.25
        self.assertEqual(grain.pixel_aspect_ratio, Fraction(1, 4))

    def test_grain_fails_with_no_metadata(self):
        with self.assertRaises(AttributeError):
            Grain(None)

    def test_grain_fails_with_bad_src_id(self):
        with self.assertRaises(AttributeError):
            Grain([], 0x44)

    def test_video_grain_fails_with_no_metadata(self):
        with self.assertRaises(AttributeError):
            VideoGrain(None)

    def test_video_grain_create_with_ots_and_no_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)

    def test_video_grain_create_with_no_ots_and_no_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(cts))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)

    def test_videograin_meta_is_json_serialisable(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(json.loads(json.dumps(grain.meta)), grain.meta)

    def test_grain_makes_videograin(self):
        meta = VIDEOGRAIN_TEST_METADATA
        data = bytearray(8192*1080)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.meta, meta)
        self.assertEqual(grain.data, data)

    def test_grain_makes_videograin_without_data(self):
        meta = VIDEOGRAIN_TEST_METADATA

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.meta, meta)
        self.assertEqual(grain.length, 0)
        self.assertEqual(grain.expected_length, 8192*1080)

    async def test_videograin_with_async_data(self):
        meta = VIDEOGRAIN_TEST_METADATA

        async def _get_data():
            _data = bytearray(8192*1080)
            for n in range(0, 16):
                _data[n] = n & 0xFF
            return _data

        data_awaitable = _get_data()
        expected_data = await _get_data()

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data_awaitable)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.meta, meta)
        self.assertIsNone(grain.data)

        self.assertEqual((await grain)[:16], expected_data[:16])
        self.assertEqual(grain.data[:16], expected_data[:16])

    async def test_videograin_with_async_data_as_acm(self):
        meta = VIDEOGRAIN_TEST_METADATA

        async def _get_data():
            _data = bytearray(8192*1080)
            for n in range(0, 16):
                _data[n] = n & 0xFF
            return _data

        data_awaitable = _get_data()
        expected_data = await _get_data()

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data_awaitable)

        self.assertEqual(grain.grain_type, "video")
        self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(grain.meta, meta)
        self.assertIsNone(grain.data)

        async with grain as _grain:
            self.assertEqual(_grain.data[:16], expected_data[:16])

    def test_video_grain_normalise(self):
        with mock.patch.object(Timestamp, "get_time", return_value=ots):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
                               rate=Fraction(25, 1),
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.origin_timestamp, ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timestamp),
                            ots)
        self.assertEqual(grain.normalise_time(grain.origin_timestamp),
                         ots.normalise(25, 1))
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timerange()),
                            TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.normalise_time(grain.origin_timerange()),
                         TimeRange.from_single_timestamp(ots).normalise(25, 1))

    def test_audio_grain_create_S16_PLANES(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_audio_format=CogAudioFormat.S16_PLANES,
                               channels=2, samples=1920, sample_rate=48000)

        self.assertEqual(grain.grain_type, "audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(ots, ots + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.media_rate, Fraction(48000, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.S16_PLANES)
        self.assertEqual(grain.channels, 2)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.sample_rate, 48000)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), 1920*2*2)
        self.assertEqual(grain.expected_length, 1920*2*2)

        self.assertEqual(repr(grain), "AudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_audio_grain_create_fills_in_missing_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(src_id, flow_id, origin_timestamp=ots,
                               cog_audio_format=CogAudioFormat.S16_PLANES,
                               channels=2, samples=1920, sample_rate=48000)

        self.assertEqual(grain.grain_type, "audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(ots, ots + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.S16_PLANES)
        self.assertEqual(grain.channels, 2)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.sample_rate, 48000)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), 1920*2*2)

        self.assertEqual(repr(grain), "AudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_audio_grain_create_fills_in_missing_ots(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(src_id, flow_id,
                               cog_audio_format=CogAudioFormat.S16_PLANES,
                               channels=2, samples=1920, sample_rate=48000)

        self.assertEqual(grain.grain_type, "audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(cts, cts + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.S16_PLANES)
        self.assertEqual(grain.channels, 2)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.sample_rate, 48000)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), 1920*2*2)

        self.assertEqual(repr(grain), "AudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_audio_grain_create_fails_with_no_params(self):
        with self.assertRaises(AttributeError):
            AudioGrain(None)

    def test_audio_grain_create_all_formats(self):
        for (fmt, length) in [(CogAudioFormat.S16_PLANES,         1920*2*2),
                              (CogAudioFormat.S16_PAIRS,          1920*2*2),
                              (CogAudioFormat.S16_INTERLEAVED,    1920*2*2),
                              (CogAudioFormat.S24_PLANES,         1920*2*4),
                              (CogAudioFormat.S24_PAIRS,          1920*2*3),
                              (CogAudioFormat.S24_INTERLEAVED,    1920*2*3),
                              (CogAudioFormat.S32_PLANES,         1920*2*4),
                              (CogAudioFormat.S32_PAIRS,          1920*2*4),
                              (CogAudioFormat.S32_INTERLEAVED,    1920*2*4),
                              (CogAudioFormat.S64_INVALID,        1920*2*8),
                              (CogAudioFormat.FLOAT_PLANES,       1920*2*4),
                              (CogAudioFormat.FLOAT_PAIRS,        1920*2*4),
                              (CogAudioFormat.FLOAT_INTERLEAVED,  1920*2*4),
                              (CogAudioFormat.DOUBLE_PLANES,      1920*2*8),
                              (CogAudioFormat.DOUBLE_PAIRS,       1920*2*8),
                              (CogAudioFormat.DOUBLE_INTERLEAVED, 1920*2*8)]:
            with mock.patch.object(Timestamp, "get_time", return_value=cts):
                grain = AudioGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                   cog_audio_format=fmt,
                                   channels=2, samples=1920, sample_rate=48000)

                self.assertEqual(grain.grain_type, "audio")
                self.assertEqual(grain.format, fmt)
                self.assertIsInstance(grain.data, bytearray)
                self.assertEqual(len(grain.data), length)

    def test_audio_grain_create_fills_in_missing_meta(self):
        meta = {}
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(meta)

        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.format, CogAudioFormat.INVALID)
        self.assertEqual(grain.channels, 0)
        self.assertEqual(grain.samples, 0)
        self.assertEqual(grain.sample_rate, 0)
        self.assertIsNone(grain.media_rate)

    def test_audio_grain_setters(self):
        meta = {}
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(meta)

        grain.format = CogAudioFormat.S16_PLANES
        self.assertEqual(grain.format, CogAudioFormat.S16_PLANES)
        grain.format = 0xA
        self.assertEqual(grain.format, CogAudioFormat.S32_INTERLEAVED)

        grain.channels = 2
        self.assertEqual(grain.channels, 2)

        grain.samples = 1920
        self.assertEqual(grain.samples, 1920)

        grain.sample_rate = 48000
        self.assertEqual(grain.sample_rate, 48000)

    def test_audiograin_meta_is_json_serialisable(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = AudioGrain(src_id, flow_id,
                               cog_audio_format=CogAudioFormat.S16_PLANES,
                               channels=2, samples=1920, sample_rate=48000)

        try:
            self.assertEqual(json.loads(json.dumps(grain.meta)), grain.meta)
        except ValueError:
            self.fail(msg="Json serialisation produces: {} which is not json deserialisable".format(json.dumps(grain.meta)))

    def test_grain_makes_audiograin(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                },
                "cog_audio": {
                    "format": CogAudioFormat.S16_PLANES,
                    "samples": 1920,
                    "channels": 6,
                    "sample_rate": 48000
                }
            },
        }

        data = bytearray(1920*6*2)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data)

        self.assertEqual(grain.grain_type, "audio")
        self.assertEqual(grain.format, CogAudioFormat.S16_PLANES)
        self.assertEqual(grain.meta, meta)
        self.assertEqual(grain.data, data)

    def test_audio_grain_normalise(self):
        with mock.patch.object(Timestamp, "get_time", return_value=ots):
            grain = AudioGrain(src_id, flow_id,
                               cog_audio_format=CogAudioFormat.S16_PLANES,
                               channels=2, samples=1920, sample_rate=48000)

        final_ts = ots + TimeOffset.from_count(1920 - 1, 48000, 1)

        self.assertEqual(grain.origin_timestamp, ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timestamp),
                            ots)
        self.assertEqual(grain.normalise_time(grain.origin_timestamp),
                         ots.normalise(48000, 1))
        self.assertEqual(grain.final_origin_timestamp(), final_ts)
        self.assertNotEqual(grain.normalise_time(grain.origin_timerange()),
                            TimeRange(ots, final_ts))
        self.assertEqual(grain.normalise_time(grain.origin_timerange()),
                         TimeRange(ots, final_ts).normalise(48000, 1))

    def test_coded_video_grain_create_VC2(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    length=1296000, cog_frame_layout=CogFrameLayout.FULL_FRAME,
                                    unit_offsets=[3, 2])

        self.assertEqual(grain.grain_type, "coded_video")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.media_rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogFrameFormat.VC2)
        self.assertEqual(grain.origin_width, 1920)
        self.assertEqual(grain.origin_height, 1080)
        self.assertEqual(grain.coded_width, 1920)
        self.assertEqual(grain.coded_height, 1080)
        self.assertEqual(grain.length, 1296000)
        self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
        self.assertEqual(grain.unit_offsets, [3, 2])
        self.assertEqual(repr(grain.unit_offsets), repr([3, 2]))

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), grain.length)

        self.assertEqual(repr(grain), "CodedVideoGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_coded_video_grain_create_fills_empty_meta(self):
        meta = {}
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(meta)

        self.assertEqual(grain.grain_type, "coded_video")
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogFrameFormat.UNKNOWN)
        self.assertEqual(grain.origin_width, 0)
        self.assertEqual(grain.origin_height, 0)
        self.assertEqual(grain.coded_width, 0)
        self.assertEqual(grain.coded_height, 0)
        self.assertEqual(grain.length, 0)
        self.assertEqual(grain.layout, CogFrameLayout.UNKNOWN)
        self.assertEqual(grain.unit_offsets, [])

    def test_coded_video_grain_create_corrects_numeric_data(self):
        meta = {
            'grain': {
                'cog_coded_frame': {
                    'format': 0x0200,
                    'layout': 0x04
                }
            }
        }

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(meta)

        self.assertEqual(grain.grain_type, "coded_video")
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogFrameFormat.MJPEG)
        self.assertEqual(grain.origin_width, 0)
        self.assertEqual(grain.origin_height, 0)
        self.assertEqual(grain.coded_width, 0)
        self.assertEqual(grain.coded_height, 0)
        self.assertEqual(grain.length, 0)
        self.assertEqual(grain.layout, CogFrameLayout.SEGMENTED_FRAME)
        self.assertEqual(grain.unit_offsets, [])

    def test_coded_video_grain_setters(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    length=1296000, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.format = CogFrameFormat.MJPEG
        self.assertEqual(grain.format, CogFrameFormat.MJPEG)

        grain.origin_width = 1
        self.assertEqual(grain.origin_width, 1)
        grain.origin_height = 2
        self.assertEqual(grain.origin_height, 2)
        grain.coded_width = 3
        self.assertEqual(grain.coded_width, 3)
        grain.coded_height = 4
        self.assertEqual(grain.coded_height, 4)
        grain.layout = CogFrameLayout.UNKNOWN
        self.assertEqual(grain.layout, CogFrameLayout.UNKNOWN)
        grain.temporal_offset = 75
        self.assertEqual(grain.temporal_offset, 75)
        grain.is_key_frame = True
        self.assertTrue(grain.is_key_frame, 75)

        self.assertNotIn('unit_offsets', grain.meta['grain']['cog_coded_frame'])
        self.assertEqual(grain.unit_offsets, [])
        grain.unit_offsets = [1, 2, 3]
        self.assertEqual(grain.unit_offsets, grain.meta['grain']['cog_coded_frame']['unit_offsets'])
        self.assertEqual(grain.unit_offsets, [1, 2, 3])
        grain.unit_offsets.append(4)
        self.assertEqual(grain.unit_offsets, grain.meta['grain']['cog_coded_frame']['unit_offsets'])
        self.assertEqual(grain.unit_offsets, [1, 2, 3, 4])
        grain.unit_offsets[0] = 35
        self.assertEqual(grain.unit_offsets, grain.meta['grain']['cog_coded_frame']['unit_offsets'])
        self.assertEqual(grain.unit_offsets, [35, 2, 3, 4])
        del grain.unit_offsets[3]
        self.assertEqual(grain.unit_offsets, grain.meta['grain']['cog_coded_frame']['unit_offsets'])
        self.assertEqual(grain.unit_offsets, [35, 2, 3])
        del grain.unit_offsets[0]
        del grain.unit_offsets[0]
        del grain.unit_offsets[0]
        self.assertNotIn('unit_offsets', grain.meta['grain']['cog_coded_frame'])
        self.assertEqual(grain.unit_offsets, [])
        with self.assertRaises(IndexError):
            del grain.unit_offsets[0]
        with self.assertRaises(IndexError):
            grain.unit_offsets[0] = 1
        grain.unit_offsets.append(1)
        self.assertEqual(grain.unit_offsets, grain.meta['grain']['cog_coded_frame']['unit_offsets'])
        self.assertEqual(grain.unit_offsets, [1])
        grain.unit_offsets = []
        self.assertNotIn('unit_offsets', grain.meta['grain']['cog_coded_frame'])
        self.assertEqual(grain.unit_offsets, [])

    def test_coded_video_grain_create_with_data(self):
        data = bytearray(500)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    cog_frame_layout=CogFrameLayout.FULL_FRAME,
                                    data=data)

        self.assertEqual(grain.data, data)
        self.assertEqual(len(grain.data), grain.length)

    def test_coded_video_grain_create_with_cts_and_ots(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id, origin_timestamp=ots,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.sync_timestamp, ots)

    def test_coded_video_grain_create_with_cts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)

    def test_coded_video_grain_create_fails_with_empty(self):
        with self.assertRaises(AttributeError):
            CodedVideoGrain(None)

    def test_coded_video_grain_meta_is_json_serialisable(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedVideoGrain(src_id, flow_id,
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(json.loads(json.dumps(grain.meta)), grain.meta)

    def test_grain_makes_codedvideograin(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_video",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                },
                "cog_coded_frame": {
                    "format": 0x0207,
                    "origin_width": 1920,
                    "origin_height": 1080,
                    "coded_width": 1920,
                    "coded_height": 1088,
                    "layout": 0x00,
                    "length": 1296000
                }
            },
        }

        data = bytearray(1296000)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data)

        self.assertEqual(grain.grain_type, "coded_video")
        self.assertEqual(grain.format, CogFrameFormat.VC2)
        self.assertEqual(grain.meta, meta)
        self.assertEqual(grain.data, data)

    def test_coded_video_grain_normalise(self):
        with mock.patch.object(Timestamp, "get_time", return_value=ots):
            grain = CodedVideoGrain(src_id, flow_id, origin_timestamp=ots,
                                    rate=Fraction(25, 1),
                                    cog_frame_format=CogFrameFormat.VC2,
                                    origin_width=1920, origin_height=1080,
                                    cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertEqual(grain.origin_timestamp, ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timestamp),
                            ots)
        self.assertEqual(grain.normalise_time(grain.origin_timestamp),
                         ots.normalise(25, 1))
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timerange()),
                            TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.normalise_time(grain.origin_timerange()),
                         TimeRange.from_single_timestamp(ots).normalise(25, 1))

    def test_coded_audio_grain_create_MP1(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                    cog_audio_format=CogAudioFormat.MP1,
                                    samples=1920,
                                    channels=6,
                                    priming=0,
                                    remainder=0,
                                    sample_rate=48000,
                                    length=15360)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(ots, ots + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.channels, 6)
        self.assertEqual(grain.priming, 0)
        self.assertEqual(grain.remainder, 0)
        self.assertEqual(grain.sample_rate, 48000)
        self.assertEqual(grain.media_rate, Fraction(48000, 1))
        self.assertEqual(grain.length, 15360)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), grain.length)

        self.assertEqual(repr(grain), "CodedAudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_coded_audio_grain_create_without_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(src_id, flow_id, origin_timestamp=ots,
                                    cog_audio_format=CogAudioFormat.MP1,
                                    samples=1920,
                                    channels=6,
                                    priming=0,
                                    remainder=0,
                                    sample_rate=48000,
                                    length=15360)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(ots, ots + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.channels, 6)
        self.assertEqual(grain.priming, 0)
        self.assertEqual(grain.remainder, 0)
        self.assertEqual(grain.sample_rate, 48000)
        self.assertEqual(grain.length, 15360)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), grain.length)

        self.assertEqual(repr(grain), "CodedAudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_coded_audio_grain_create_without_sts_or_ots(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(src_id, flow_id,
                                    cog_audio_format=CogAudioFormat.MP1,
                                    samples=1920,
                                    channels=6,
                                    priming=0,
                                    remainder=0,
                                    sample_rate=48000,
                                    length=15360)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts + TimeOffset.from_count(1919, 48000, 1))
        self.assertEqual(grain.origin_timerange(), TimeRange(cts, cts + TimeOffset.from_count(1919, 48000, 1)))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        self.assertEqual(grain.samples, 1920)
        self.assertEqual(grain.channels, 6)
        self.assertEqual(grain.priming, 0)
        self.assertEqual(grain.remainder, 0)
        self.assertEqual(grain.sample_rate, 48000)
        self.assertEqual(grain.length, 15360)

        self.assertIsInstance(grain.data, bytearray)
        self.assertEqual(len(grain.data), grain.length)

        self.assertEqual(repr(grain), "CodedAudioGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    def test_coded_audio_grain_create_fills_empty_meta(self):
        meta = {}

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(meta)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.INVALID)
        self.assertEqual(grain.samples, 0)
        self.assertEqual(grain.channels, 0)
        self.assertEqual(grain.priming, 0)
        self.assertEqual(grain.remainder, 0)
        self.assertEqual(grain.sample_rate, 48000)
        self.assertEqual(grain.length, 0)

    def test_coded_audio_grain_create_corrects_numeric_data(self):
        meta = {
            'grain': {
                'cog_coded_audio': {
                    'format': 0x200
                }
            }
        }

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(meta)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        self.assertEqual(grain.samples, 0)
        self.assertEqual(grain.channels, 0)
        self.assertEqual(grain.priming, 0)
        self.assertEqual(grain.remainder, 0)
        self.assertEqual(grain.sample_rate, 48000)
        self.assertEqual(grain.length, 0)

    def test_coded_audio_grain_setters(self):
        meta = {}

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(meta)

        grain.format = CogAudioFormat.MP1
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        grain.format = 0x202
        self.assertEqual(grain.format, CogAudioFormat.OPUS)

        grain.channels = 2
        self.assertEqual(grain.channels, 2)

        grain.samples = 1920
        self.assertEqual(grain.samples, 1920)

        grain.priming = 12
        self.assertEqual(grain.priming, 12)

        grain.remainder = 105
        self.assertEqual(grain.remainder, 105)

        grain.sample_rate = 48000
        self.assertEqual(grain.sample_rate, 48000)

    def test_coded_audio_grain_with_data(self):
        meta = {}
        data = bytearray(15360)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(meta, data)

        self.assertEqual(grain.length, len(data))
        self.assertEqual(grain.data, data)

    def test_coded_audio_grain_raises_on_empty(self):
        with self.assertRaises(AttributeError):
            CodedAudioGrain(None)

    def test_codedaudiograin_meta_is_json_serialisable(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = CodedAudioGrain(src_id, flow_id,
                                    cog_audio_format=CogAudioFormat.MP1,
                                    samples=1920,
                                    channels=6,
                                    priming=0,
                                    remainder=0,
                                    sample_rate=48000,
                                    length=15360)

        try:
            self.assertEqual(json.loads(json.dumps(grain.meta)), grain.meta)
        except ValueError:
            self.fail(msg="Json serialisation produces: {} which is not json deserialisable".format(json.dumps(grain.meta)))

    def test_grain_makes_codedaudiograin(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_audio",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                },
                "cog_coded_audio": {
                    "format": CogAudioFormat.MP1,
                    "samples": 1920,
                    "channels": 6,
                    "priming": 12,
                    "remainder": 105,
                    "sample_rate": 48000
                }
            },
        }

        data = bytearray(15360)

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data=data)

        self.assertEqual(grain.grain_type, "coded_audio")
        self.assertEqual(grain.format, CogAudioFormat.MP1)
        self.assertEqual(grain.meta, meta)
        self.assertEqual(grain.data, data)

    def test_coded_audio_grain_normalise(self):
        with mock.patch.object(Timestamp, "get_time", return_value=ots):
            grain = CodedAudioGrain(src_id, flow_id, origin_timestamp=ots,
                                    cog_audio_format=CogAudioFormat.MP1,
                                    samples=1920,
                                    channels=6,
                                    priming=0,
                                    remainder=0,
                                    sample_rate=48000,
                                    length=15360)

        final_ts = ots + TimeOffset.from_count(1920 - 1, 48000, 1)

        self.assertEqual(grain.origin_timestamp, ots)
        self.assertNotEqual(grain.normalise_time(grain.origin_timestamp),
                            ots)
        self.assertEqual(grain.normalise_time(grain.origin_timestamp),
                         ots.normalise(48000, 1))
        self.assertEqual(grain.final_origin_timestamp(), final_ts)
        self.assertNotEqual(grain.normalise_time(grain.origin_timerange()),
                            TimeRange(ots, final_ts))
        self.assertEqual(grain.normalise_time(grain.origin_timerange()),
                         TimeRange(ots, final_ts).normalise(48000, 1))

    def test_event_grain_create(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = EventGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               event_type='urn:x-ipstudio:format:event.query', topic='/dummy')

        self.assertEqual(grain.grain_type, "event")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertIsNone(grain.media_rate)
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.event_type, "urn:x-ipstudio:format:event.query")
        self.assertEqual(grain.topic, "/dummy")
        self.assertEqual(grain.event_data, [])
        self.assertEqual(json.loads(grain.data.decode('utf-8')), {'type': "urn:x-ipstudio:format:event.query",
                                                                  'topic': "/dummy",
                                                                  'data': []})

        self.assertEqual(repr(grain), "EventGrain({!r})".format(grain.meta))

    def test_event_grain_create_without_sts(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = EventGrain(src_id, flow_id, origin_timestamp=ots,
                               event_type='urn:x-ipstudio:format:event.query', topic='/dummy')

        self.assertEqual(grain.grain_type, "event")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.event_type, "urn:x-ipstudio:format:event.query")
        self.assertEqual(grain.topic, "/dummy")
        self.assertEqual(grain.event_data, [])

        self.assertEqual(repr(grain), "EventGrain({!r})".format(grain.meta))

    def test_event_grain_create_without_sts_or_ots(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = EventGrain(src_id, flow_id,
                               event_type='urn:x-ipstudio:format:event.query', topic='/dummy')

        self.assertEqual(grain.grain_type, "event")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(cts))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.event_type, "urn:x-ipstudio:format:event.query")
        self.assertEqual(grain.topic, "/dummy")
        self.assertEqual(grain.event_data, [])

        self.assertEqual(repr(grain), "EventGrain({!r})".format(grain.meta))

    def test_event_grain_create_fills_in_empty_meta(self):
        meta = {}

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = EventGrain(meta)

        self.assertEqual(grain.grain_type, "event")
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.final_origin_timestamp(), cts)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(cts))
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0, 1))
        self.assertEqual(grain.duration, Fraction(0, 1))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.event_type, "")
        self.assertEqual(grain.topic, "")
        self.assertEqual(grain.event_data, [])

    def test_event_grain_create_fails_on_None(self):
        with self.assertRaises(AttributeError):
            EventGrain(None)

    def test_event_grain_create_from_meta_and_data(self):
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "event",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(ots),
                "sync_timestamp": str(sts),
                "creation_timestamp": str(cts),
                "rate": {
                    "numerator": 25,
                    "denominator": 1,
                },
                "duration": {
                    "numerator": 1,
                    "denominator": 25,
                }
            }
        }
        data = json.dumps({
            'type': 'urn:x-ipstudio:format:event.notify',
            'topic': '/foo',
            'data': [
                {
                    'path': '/bar',
                    'pre': 'baz'
                },
                {
                    'path': '/beep',
                    'pre': 'boop',
                    'post': 'bong'
                }
            ]
        })

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(meta, data.encode('utf-8'))

        self.assertEqual(grain.grain_type, "event")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.final_origin_timestamp(), ots)
        self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(25, 1))
        self.assertEqual(grain.duration, Fraction(1, 25))
        self.assertEqual(grain.timelabels, [])
        self.assertEqual(grain.event_type, "urn:x-ipstudio:format:event.notify")
        self.assertEqual(grain.topic, "/foo")
        self.assertEqual(len(grain.event_data), 2)
        self.assertEqual(len(grain.event_data[0]), 2)
        self.assertEqual(grain.event_data[0].path, '/bar')
        self.assertEqual(grain.event_data[0].pre, 'baz')
        self.assertIsNone(grain.event_data[0].post)
        self.assertEqual(len(grain.event_data[1]), 3)
        self.assertEqual(grain.event_data[1].path, '/beep')
        self.assertEqual(grain.event_data[1].pre, 'boop')
        self.assertEqual(grain.event_data[1].post, 'bong')

    def test_event_grain_setters(self):
        meta = {}

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = EventGrain(meta)

        grain.event_type = "urn:x-ipstudio:format:event.potato"
        self.assertEqual(grain.event_type, "urn:x-ipstudio:format:event.potato")
        grain.topic = "/important/data"
        self.assertEqual(grain.topic, "/important/data")
        grain.append('/sub/path', 'was', 'is')
        self.assertEqual(len(grain.event_data), 1)
        self.assertEqual(grain.event_data[0], {'path': '/sub/path',
                                               'pre': 'was',
                                               'post': 'is'})
        self.assertEqual(grain.event_data[0].path, '/sub/path')
        self.assertEqual(grain.event_data[0].pre, 'was')
        self.assertEqual(grain.event_data[0].post, 'is')
        grain.event_data[0].path = '/location'
        grain.event_data[0].pre = 'now'
        grain.event_data[0].post = 'next'
        self.assertEqual(grain.event_data[0], {'path': '/location',
                                               'pre': 'now',
                                               'post': 'next'})
        self.assertEqual(json.loads(grain.data.decode('utf-8')), {'type': "urn:x-ipstudio:format:event.potato",
                                                                  'topic': "/important/data",
                                                                  'data': [{'path': '/location',
                                                                            'pre': 'now',
                                                                            'post': 'next'}]})
        grain.event_data[0]['post'] = 'never'
        del grain.event_data[0]['post']
        self.assertIsNone(grain.event_data[0].post)

        grain.event_data[0].pre = None
        grain.event_data[0].post = 'never_was'
        grain.event_data[0].post = None
        grain.event_data[0].post = None
        self.assertNotIn('pre', grain.event_data[0])
        self.assertIsNone(grain.event_data[0].pre)

        grain.event_data = []
        self.assertEqual(len(grain.event_data), 0)
        self.assertEqual(json.loads(grain.data.decode('utf-8')), {'type': "urn:x-ipstudio:format:event.potato",
                                                                  'topic': "/important/data",
                                                                  'data': []})

        grain.data = json.dumps({'type': "urn:x-ipstudio:format:event.potato",
                                 'topic': "/important/data",
                                 'data': [{'path': '/location',
                                           'pre': 'now',
                                           'post': 'next'}]})
        self.assertEqual(json.loads(grain.data.decode('utf-8')), {'type': "urn:x-ipstudio:format:event.potato",
                                                                  'topic': "/important/data",
                                                                  'data': [{'path': '/location',
                                                                            'pre': 'now',
                                                                            'post': 'next'}]})

        with self.assertRaises(ValueError):
            grain.data = bytearray(json.dumps({'potato': "masher"}).encode('utf-8'))

    def test_copy(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.data[0] = 0x1B
        grain.data[1] = 0xBC

        clone = copy(grain)

        self.assertEqual(grain.data[0], clone.data[0])
        self.assertEqual(grain.data[1], clone.data[1])

        grain.data[0] = 0xCA
        grain.data[1] = 0xFE

        self.assertEqual(grain.data[0], clone.data[0])
        self.assertEqual(grain.data[1], clone.data[1])

    def test_deepcopy(self):
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.data[0] = 0x1B
        grain.data[1] = 0xBC

        clone = deepcopy(grain)

        self.assertEqual(grain.data[0], clone.data[0])
        self.assertEqual(grain.data[1], clone.data[1])

        grain.data[0] = 0xCA
        grain.data[1] = 0xFE

        self.assertNotEqual(grain.data[0], clone.data[0])
        self.assertNotEqual(grain.data[1], clone.data[1])
