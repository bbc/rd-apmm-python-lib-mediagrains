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

import numpy as np


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

        self.assertIsInstance(grain.components[0].data, np.ndarray)
        self.assertEqual(grain.components[0].data.nbytes, 1920*1080*2)
        self.assertEqual(grain.components[0].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[0].data.size, 1920*1080)
        self.assertEqual(grain.components[0].data.itemsize, 2)
        self.assertEqual(grain.components[0].data.ndim, 2)
        self.assertEqual(grain.components[0].data.shape, (1920, 1080))

        self.assertIsInstance(grain.components[1].data, np.ndarray)
        self.assertEqual(grain.components[1].data.nbytes, 1920*1080)
        self.assertEqual(grain.components[1].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[1].data.size, 1920*1080//2)
        self.assertEqual(grain.components[1].data.itemsize, 2)
        self.assertEqual(grain.components[1].data.ndim, 2)
        self.assertEqual(grain.components[1].data.shape, (1920//2, 1080))

        self.assertIsInstance(grain.components[2].data, np.ndarray)
        self.assertEqual(grain.components[2].data.nbytes, 1920*1080)
        self.assertEqual(grain.components[2].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[2].data.size, 1920*1080//2)
        self.assertEqual(grain.components[2].data.itemsize, 2)
        self.assertEqual(grain.components[2].data.ndim, 2)
        self.assertEqual(grain.components[2].data.shape, (1920//2, 1080))

        self.assertEqual(grain.expected_length, 1920*1080*4)

        # Test that changes to the component arrays are reflected in the main data array
        for y in range(0, 16):
            for x in range(0, 8):
                grain.components[0].data[2*x + 0, y] = (y*1920 + 2*x + 0)&0xFF
                grain.components[1].data[x, y] = (y*1920//2 + x)&0xFF + 0x100
                grain.components[0].data[2*x + 1, y] = (y*1920 + 2*x + 1)&0xFF
                grain.components[2].data[x, y] = (y*1920//2 + x)&0xFF + 0x200

        for y in range(0, 16):
            for x in range(0, 8):
                self.assertEqual(grain.data[y*1920 + 2*x + 0], (y*1920 + 2*x + 0)&0xFF)
                self.assertEqual(grain.data[y*1920 + 2*x + 1], (y*1920 + 2*x + 1)&0xFF)
                self.assertEqual(grain.data[1920*1080 + y*1920//2 + x], (y*1920//2 + x)&0xFF + 0x100)
                self.assertEqual(grain.data[3*1920*1080//2 + y*1920//2 + x], (y*1920//2 + x)&0xFF + 0x200)

    def test_video_grain_create_YUV444_10bit(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_444_10BIT,
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
        self.assertEqual(grain.format, CogFrameFormat.S16_444_10BIT)
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

        self.assertEqual(grain.components[1].stride, 1920*2)
        self.assertEqual(grain.components[1].width, 1920)
        self.assertEqual(grain.components[1].height, 1080)
        self.assertEqual(grain.components[1].offset, 1920*1080*2)
        self.assertEqual(grain.components[1].length, 1920*1080*2)
        self.assertEqual(len(grain.components[1]), 5)

        self.assertEqual(grain.components[2].stride, 1920*2)
        self.assertEqual(grain.components[2].width, 1920)
        self.assertEqual(grain.components[2].height, 1080)
        self.assertEqual(grain.components[2].offset, 1920*1080*4)
        self.assertEqual(grain.components[2].length, 1920*1080*2)
        self.assertEqual(len(grain.components[2]), 5)

        self.assertIsInstance(grain.data, np.ndarray)
        self.assertEqual(grain.data.nbytes, 1920*1080*2*3)
        self.assertEqual(grain.data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.data.size, 1920*1080*3)
        self.assertEqual(grain.data.itemsize, 2)
        self.assertEqual(grain.data.ndim, 1)
        self.assertEqual(grain.data.shape, (1920*1080*3,))

        self.assertEqual(repr(grain), "VideoGrain({!r},< numpy data of length {} >)".format(grain.meta, len(grain.data)))

        self.assertIsInstance(grain.components[0].data, np.ndarray)
        self.assertEqual(grain.components[0].data.nbytes, 1920*1080*2)
        self.assertEqual(grain.components[0].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[0].data.size, 1920*1080)
        self.assertEqual(grain.components[0].data.itemsize, 2)
        self.assertEqual(grain.components[0].data.ndim, 2)
        self.assertEqual(grain.components[0].data.shape, (1920, 1080))

        self.assertIsInstance(grain.components[1].data, np.ndarray)
        self.assertEqual(grain.components[1].data.nbytes, 1920*1080*2)
        self.assertEqual(grain.components[1].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[1].data.size, 1920*1080)
        self.assertEqual(grain.components[1].data.itemsize, 2)
        self.assertEqual(grain.components[1].data.ndim, 2)
        self.assertEqual(grain.components[1].data.shape, (1920, 1080))

        self.assertIsInstance(grain.components[2].data, np.ndarray)
        self.assertEqual(grain.components[2].data.nbytes, 1920*1080*2)
        self.assertEqual(grain.components[2].data.dtype, np.dtype(np.int16))
        self.assertEqual(grain.components[2].data.size, 1920*1080)
        self.assertEqual(grain.components[2].data.itemsize, 2)
        self.assertEqual(grain.components[2].data.ndim, 2)
        self.assertEqual(grain.components[2].data.shape, (1920, 1080))

        self.assertEqual(grain.expected_length, 1920*1080*2*3)

        # Test that changes to the component arrays are reflected in the main data array
        for y in range(0, 16):
            for x in range(0, 16):
                grain.components[0].data[x, y] = (y*1920 + x)&0xFF
                grain.components[1].data[x, y] = (y*1920 + x)&0xFF + 0x100
                grain.components[2].data[x, y] = (y*1920 + x)&0xFF + 0x200

        for y in range(0, 16):
            for x in range(0, 16):
                self.assertEqual(grain.data[y*1920 + x], (y*1920 + x)&0xFF)
                self.assertEqual(grain.data[1920*1080 + y*1920 + x], (y*1920 + x)&0xFF + 0x100)
                self.assertEqual(grain.data[2*1920*1080 + y*1920 + x], (y*1920 + x)&0xFF + 0x200)

    def test_copy(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.data[0] = 0x1BBC

        clone = copy(grain)

        self.assertEqual(grain.data[0], clone.data[0])

        grain.data[0] = 0xCAFE

        self.assertEqual(grain.data[0], clone.data[0])

    def test_deepcopy(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        grain.data[0] = 0x1BBC

        clone = deepcopy(grain)

        self.assertEqual(grain.data[0], clone.data[0])

        grain.data[0] = 0xCAFE

        self.assertNotEqual(grain.data[0], clone.data[0])
