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

from unittest import TestCase

import uuid
from mediagrains.numpy import VideoGrain
from mediagrains.cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat
from mediatimestamp.immutable import Timestamp, TimeOffset, TimeRange
import mock
from fractions import Fraction
import json
from copy import copy, deepcopy


class TestGrain (TestCase):
    def test_video_grain_create_YUV422_10bit(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

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

        self.assertIsInstance(grain.data, np.ndarray)
        self.assertEqual(grain.data.nbytes, 1920*1080*2*2)
        self.assertEqual(grain.data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.data.size, 1920*1080*2)
        self.assertEqual(grain.data.itemsize, 2)
        self.assertEqual(grain.data.ndim, 1)
        self.assertEqual(grain.data.shape, (1920*1080*2,))

        self.assertEqual(repr(grain), "VideoGrain({!r},< numpy data of length {} >)".format(grain.meta, len(grain.data)))

        self.assertEqual(len(grain.components), 3)
        self.assertEqual(grain.components[0].stride, 1920*2)
        self.assertEqual(grain.components[0].width, 1920)
        self.assertEqual(grain.components[0].height, 1080)
        self.assertEqual(grain.components[0].offset, 0)
        self.assertEqual(grain.components[0].length, 1920*1080*2)
        self.assertIsInstance(grain.components[0].data, np.ndarray)
        self.assertEqual(grain.components[0].data.nbytes, 1920*1080*2)
        self.assertEqual(grain.components[0].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[0].data.size, 1920*1080)
        self.assertEqual(grain.components[0].data.itemsize, 2)
        self.assertEqual(grain.components[0].data.ndim, 2)
        self.assertEqual(grain.components[0].data.shape, (1920, 1080))

        self.assertEqual(grain.components[1].stride, 1920)
        self.assertEqual(grain.components[1].width, 1920//2)
        self.assertEqual(grain.components[1].height, 1080)
        self.assertEqual(grain.components[1].offset, 1920*1080*2)
        self.assertEqual(grain.components[1].length, 1920*1080)
        self.assertIsInstance(grain.components[1].data, np.ndarray)
        self.assertEqual(grain.components[1].data.nbytes, 1920*1080)
        self.assertEqual(grain.components[1].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[1].data.size, 1920*1080//2)
        self.assertEqual(grain.components[1].data.itemsize, 2)
        self.assertEqual(grain.components[1].data.ndim, 2)
        self.assertEqual(grain.components[1].data.shape, (1920//2, 1080))

        self.assertEqual(grain.components[2].stride, 1920)
        self.assertEqual(grain.components[2].width, 1920//2)
        self.assertEqual(grain.components[2].height, 1080)
        self.assertEqual(grain.components[2].offset, 1920*1080*3)
        self.assertEqual(grain.components[2].length, 1920*1080)
        self.assertIsInstance(grain.components[2].data, np.ndarray)
        self.assertEqual(grain.components[2].data.nbytes, 1920*1080)
        self.assertEqual(grain.components[2].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[2].data.size, 1920*1080//2)
        self.assertEqual(grain.components[2].data.itemsize, 2)
        self.assertEqual(grain.components[2].data.ndim, 2)
        self.assertEqual(grain.components[2].data.shape, (1920//2, 1080))

        self.assertEqual(grain.expected_length, 1920*1080*4)

        # Test that changes to the component arrays are reflected in the main data array
        for y in range(0, 1080):
            for x in range(0, 1920//2):
                grain.components[0].data[2*x + 0, y] = (y*1920 + 2*x + 0)&0xFF
                grain.components[1].data[x, y] = (y*1920//2 + x)&0xFF + 0x100
                grain.components[0].data[2*x + 1, y] = (y*1920 + 2*x + 1)&0x3FF
                grain.components[2].data[x, y] = (y*1920//2 + x)&0xFF + 0x200

        for n in range(0, 1920*1080):
            self.assertEqual(grain.data[n], n&0xFF)
        for n in range(0, 1920*1080//2):
            self.assertEqual(grain.data[1920*1080 + n], n&0xFF + 0x100)
        for n in range(0, 1920*1080//2):
            self.assertEqual(grain.data[3*1920*1080//2 + n], n&0xFF + 0x200)


    # def test_video_grain_create_sizes(self):
    #     for (fmt, complens) in [
    #             (CogFrameFormat.S32_444, (1920*1080*4, 1920*1080*4, 1920*1080*4)),
    #             (CogFrameFormat.S32_422, (1920*1080*4, 1920*1080*2, 1920*1080*2)),
    #             (CogFrameFormat.S32_420, (1920*1080*4, 1920*1080, 1920*1080)),
    #             (CogFrameFormat.S16_444_10BIT, (1920*1080*2, 1920*1080*2, 1920*1080*2)),
    #             (CogFrameFormat.S16_422_10BIT, (1920*1080*2, 1920*1080, 1920*1080)),
    #             (CogFrameFormat.S16_420_10BIT, (1920*1080*2, 1920*1080/2, 1920*1080/2)),
    #             (CogFrameFormat.U8_444, (1920*1080, 1920*1080, 1920*1080)),
    #             (CogFrameFormat.U8_422, (1920*1080, 1920*1080/2, 1920*1080/2)),
    #             (CogFrameFormat.U8_420, (1920*1080, 1920*1080/4, 1920*1080/4)),
    #             (CogFrameFormat.UYVY, (1920*1080*2,)),
    #             (CogFrameFormat.RGB, (1920*1080*3,)),
    #             (CogFrameFormat.RGBA, (1920*1080*4,)),
    #             (CogFrameFormat.v210, (40*128*1080,)),
    #             (CogFrameFormat.v216, (1920*1080*4,)),
    #             (CogFrameFormat.UNKNOWN, ()),
    #             ]:
    #         src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #         flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #         cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #         ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #         sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #         with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #             grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                                cog_frame_format=fmt,
    #                                width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #         self.assertEqual(len(grain.components), len(complens))
    #         offset = 0
    #         for (complen, comp) in zip(complens, grain.components):
    #             self.assertEqual(complen, comp.length)
    #             self.assertEqual(offset, comp.offset)
    #             offset += complen

    #         self.assertEqual(len(grain.data), offset)

    # def test_video_component_setters(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     grain.components[0].stride = 23
    #     self.assertEqual(grain.components[0].stride, 23)
    #     grain.components[0].width = 23
    #     self.assertEqual(grain.components[0].width, 23)
    #     grain.components[0].height = 23
    #     self.assertEqual(grain.components[0].height, 23)
    #     grain.components[0].offset = 23
    #     self.assertEqual(grain.components[0].offset, 23)
    #     grain.components[0].length = 23
    #     self.assertEqual(grain.components[0].length, 23)

    #     grain.components[0]['length'] = 17
    #     self.assertEqual(grain.components[0].length, 17)

    #     grain.components[0]['potato'] = 3
    #     self.assertIn('potato', grain.components[0])
    #     self.assertEqual(grain.components[0]['potato'], 3)
    #     del grain.components[0]['potato']
    #     self.assertNotIn('potato', grain.components[0])

    #     grain.components.append({'stride': 1920,
    #                              'width': 1920,
    #                              'height': 1080,
    #                              'offset': 1920*1080*2*2,
    #                              'length': 1920*1080})

    #     self.assertEqual(grain.components[3].stride, 1920)
    #     self.assertEqual(grain.components[3].width, 1920)
    #     self.assertEqual(grain.components[3].height, 1080)
    #     self.assertEqual(grain.components[3].offset, 1920*1080*2*2)
    #     self.assertEqual(grain.components[3].length, 1920*1080)

    #     self.assertEqual(len(grain.components), 4)
    #     del grain.components[3]
    #     self.assertEqual(len(grain.components), 3)

    #     grain.components[0] = {'stride': 1920,
    #                            'width': 1920,
    #                            'height': 1080,
    #                            'offset': 1920*1080*2*2,
    #                            'length': 1920*1080}

    #     self.assertEqual(grain.components[0].stride, 1920)
    #     self.assertEqual(grain.components[0].width, 1920)
    #     self.assertEqual(grain.components[0].height, 1080)
    #     self.assertEqual(grain.components[0].offset, 1920*1080*2*2)
    #     self.assertEqual(grain.components[0].length, 1920*1080)

    # def test_video_grain_with_sparse_meta(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     meta = {
    #         "@_ns": "urn:x-ipstudio:ns:0.1",
    #         "grain": {
    #             "grain_type": "video",
    #             "source_id": str(src_id),
    #             "flow_id": str(flow_id),
    #             "origin_timestamp": str(ots),
    #             "sync_timestamp": str(sts),
    #             "creation_timestamp": str(cts),
    #             "rate": {
    #                 "numerator": 25,
    #                 "denominator": 1,
    #                 },
    #             "duration": {
    #                 "numerator": 1,
    #                 "denominator": 25,
    #                 }
    #         },
    #     }

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(meta)

    #     self.assertEqual(grain.format, CogFrameFormat.UNKNOWN)
    #     self.assertEqual(grain.width, 0)
    #     self.assertEqual(grain.height, 0)
    #     self.assertEqual(grain.layout, CogFrameLayout.UNKNOWN)
    #     self.assertEqual(grain.extension, 0)
    #     self.assertEqual(len(grain.components), 0)

    # def test_video_grain_with_numeric_identifiers(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                            cog_frame_format=0x2805,
    #                            width=1920, height=1080,
    #                            cog_frame_layout=0)

    #     self.assertEqual(grain.grain_type, "video")
    #     self.assertEqual(grain.source_id, src_id)
    #     self.assertEqual(grain.flow_id, flow_id)
    #     self.assertEqual(grain.origin_timestamp, ots)
    #     self.assertEqual(grain.final_origin_timestamp(), ots)
    #     self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
    #     self.assertEqual(grain.sync_timestamp, sts)
    #     self.assertEqual(grain.creation_timestamp, cts)
    #     self.assertEqual(grain.rate, Fraction(25, 1))
    #     self.assertEqual(grain.duration, Fraction(1, 25))
    #     self.assertEqual(grain.timelabels, [])
    #     self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
    #     self.assertEqual(grain.width, 1920)
    #     self.assertEqual(grain.height, 1080)
    #     self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
    #     self.assertEqual(grain.extension, 0)
    #     self.assertIsNone(grain.source_aspect_ratio)
    #     self.assertIsNone(grain.pixel_aspect_ratio)

    #     self.assertEqual(len(grain.components), 3)
    #     self.assertEqual(grain.components[0].stride, 1920*2)
    #     self.assertEqual(grain.components[0].width, 1920)
    #     self.assertEqual(grain.components[0].height, 1080)
    #     self.assertEqual(grain.components[0].offset, 0)
    #     self.assertEqual(grain.components[0].length, 1920*1080*2)

    #     self.assertEqual(grain.components[1].stride, 1920)
    #     self.assertEqual(grain.components[1].width, 1920/2)
    #     self.assertEqual(grain.components[1].height, 1080)
    #     self.assertEqual(grain.components[1].offset, 1920*1080*2)
    #     self.assertEqual(grain.components[1].length, 1920*1080)

    #     self.assertEqual(grain.components[2].stride, 1920)
    #     self.assertEqual(grain.components[2].width, 1920/2)
    #     self.assertEqual(grain.components[2].height, 1080)
    #     self.assertEqual(grain.components[2].offset, 1920*1080*2 + 1920*1080)
    #     self.assertEqual(grain.components[2].length, 1920*1080)

    #     self.assertIsInstance(grain.data, bytearray)
    #     self.assertEqual(len(grain.data), 1920*1080*2*2)

    #     self.assertEqual(repr(grain), "VideoGrain({!r},< binary data of length {} >)".format(grain.meta, len(grain.data)))

    #     self.assertEqual(dict(grain.components[0]), {'stride': 1920*2,
    #                                                  'width': 1920,
    #                                                  'height': 1080,
    #                                                  'offset': 0,
    #                                                  'length': 1920*1080*2})

    # def test_video_grain_setters(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     grain.format = CogFrameFormat.S16_444
    #     self.assertEqual(grain.format, CogFrameFormat.S16_444)
    #     grain.format = 0x0207
    #     self.assertEqual(grain.format, CogFrameFormat.VC2)

    #     grain.width = 2
    #     self.assertEqual(grain.width, 2)

    #     grain.height = 13
    #     self.assertEqual(grain.height, 13)

    #     grain.layout = CogFrameLayout.SEPARATE_FIELDS
    #     self.assertEqual(grain.layout, CogFrameLayout.SEPARATE_FIELDS)
    #     grain.layout = 0x02
    #     self.assertEqual(grain.layout, CogFrameLayout.SINGLE_FIELD)

    #     grain.extension = 1
    #     self.assertEqual(grain.extension, 1)

    #     grain.source_aspect_ratio = 50
    #     self.assertEqual(grain.source_aspect_ratio, Fraction(50, 1))

    #     grain.pixel_aspect_ratio = 0.25
    #     self.assertEqual(grain.pixel_aspect_ratio, Fraction(1, 4))

    # def test_video_grain_fails_with_no_metadata(self):
    #     with self.assertRaises(AttributeError):
    #         VideoGrain(None)

    # def test_video_grain_create_with_ots_and_no_sts(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     self.assertEqual(grain.origin_timestamp, ots)
    #     self.assertEqual(grain.final_origin_timestamp(), ots)
    #     self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
    #     self.assertEqual(grain.sync_timestamp, ots)
    #     self.assertEqual(grain.creation_timestamp, cts)

    # def test_video_grain_create_with_no_ots_and_no_sts(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     self.assertEqual(grain.origin_timestamp, cts)
    #     self.assertEqual(grain.final_origin_timestamp(), cts)
    #     self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(cts))
    #     self.assertEqual(grain.sync_timestamp, cts)
    #     self.assertEqual(grain.creation_timestamp, cts)

    # def test_videograin_meta_is_json_serialisable(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     self.assertEqual(json.loads(json.dumps(grain.meta)), grain.meta)

    # def test_video_grain_normalise(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")

    #     with mock.patch.object(Timestamp, "get_time", return_value=ots):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots,
    #                            rate=Fraction(25, 1),
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     self.assertEqual(grain.origin_timestamp, ots)
    #     self.assertNotEqual(grain.normalise_time(grain.origin_timestamp),
    #                         ots)
    #     self.assertEqual(grain.normalise_time(grain.origin_timestamp),
    #                      ots.normalise(25, 1))
    #     self.assertEqual(grain.final_origin_timestamp(), ots)
    #     self.assertNotEqual(grain.normalise_time(grain.origin_timerange()),
    #                         TimeRange.from_single_timestamp(ots))
    #     self.assertEqual(grain.normalise_time(grain.origin_timerange()),
    #                      TimeRange.from_single_timestamp(ots).normalise(25, 1))

    # def test_copy(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     grain.data[0] = 0x1B
    #     grain.data[1] = 0xBC

    #     clone = copy(grain)

    #     self.assertEqual(grain.data[0], clone.data[0])
    #     self.assertEqual(grain.data[1], clone.data[1])

    #     grain.data[0] = 0xCA
    #     grain.data[1] = 0xFE

    #     self.assertEqual(grain.data[0], clone.data[0])
    #     self.assertEqual(grain.data[1], clone.data[1])

    # def test_deepcopy(self):
    #     src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
    #     flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
    #     cts = Timestamp.from_tai_sec_nsec("417798915:0")
    #     ots = Timestamp.from_tai_sec_nsec("417798915:5")
    #     sts = Timestamp.from_tai_sec_nsec("417798915:10")

    #     with mock.patch.object(Timestamp, "get_time", return_value=cts):
    #         grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
    #                            cog_frame_format=CogFrameFormat.S16_422_10BIT,
    #                            width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

    #     grain.data[0] = 0x1B
    #     grain.data[1] = 0xBC

    #     clone = deepcopy(grain)

    #     self.assertEqual(grain.data[0], clone.data[0])
    #     self.assertEqual(grain.data[1], clone.data[1])

    #     grain.data[0] = 0xCA
    #     grain.data[1] = 0xFE

    #     self.assertNotEqual(grain.data[0], clone.data[0])
    #     self.assertNotEqual(grain.data[1], clone.data[1])
