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
from mediagrains.cogenums import (
    CogFrameFormat,
    CogFrameLayout,
    COG_FRAME_FORMAT_BYTES_PER_VALUE,
    COG_FRAME_FORMAT_H_SHIFT,
    COG_FRAME_FORMAT_V_SHIFT)
from mediatimestamp.immutable import Timestamp, TimeRange
import mock
from fractions import Fraction
from copy import copy, deepcopy

import numpy as np


class TestGrain (TestCase):
    def assertIsVideoGrain(self,
                           fmt,
                           src_id=uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429"),
                           flow_id=uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb"),
                           ots=Timestamp.from_tai_sec_nsec("417798915:5"),
                           sts=Timestamp.from_tai_sec_nsec("417798915:10"),
                           cts=Timestamp.from_tai_sec_nsec("417798915:0"),
                           rate=Fraction(25, 1),
                           width=1920,
                           height=1080):
        def __inner(grain):
            self.assertEqual(grain.grain_type, "video")
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ots)
            self.assertEqual(grain.final_origin_timestamp(), ots)
            self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
            self.assertEqual(grain.sync_timestamp, sts)
            self.assertEqual(grain.creation_timestamp, cts)
            self.assertEqual(grain.rate, rate)
            self.assertEqual(grain.duration, 1/rate)
            self.assertEqual(grain.timelabels, [])
            self.assertEqual(grain.format, fmt)
            self.assertEqual(grain.width, width)
            self.assertEqual(grain.height, height)
            self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
            self.assertEqual(grain.extension, 0)
            self.assertIsNone(grain.source_aspect_ratio)
            self.assertIsNone(grain.pixel_aspect_ratio)

            bps = COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt)
            hs = COG_FRAME_FORMAT_H_SHIFT(fmt)
            vs = COG_FRAME_FORMAT_V_SHIFT(fmt)

            self.assertEqual(len(grain.components), 3)
            self.assertEqual(grain.components[0].stride, width*bps)
            self.assertEqual(grain.components[0].width, width)
            self.assertEqual(grain.components[0].height, height)
            self.assertEqual(grain.components[0].offset, 0)
            self.assertEqual(grain.components[0].length, width*height*bps)
            self.assertEqual(len(grain.components[0]), 5)

            self.assertEqual(grain.components[1].stride, width*bps >> hs)
            self.assertEqual(grain.components[1].width, width >> hs)
            self.assertEqual(grain.components[1].height, height >> vs)
            self.assertEqual(grain.components[1].offset, width*height*bps)
            self.assertEqual(grain.components[1].length, width*height*bps >> (hs + vs))
            self.assertEqual(len(grain.components[1]), 5)

            self.assertEqual(grain.components[2].stride, width*bps >> hs)
            self.assertEqual(grain.components[2].width, width >> hs)
            self.assertEqual(grain.components[2].height, height >> vs)
            self.assertEqual(grain.components[2].offset, width*height*bps + (width*height*bps >> (hs + vs)))
            self.assertEqual(grain.components[2].length, width*height*bps >> (hs + vs))
            self.assertEqual(len(grain.components[2]), 5)

            if bps == 1:
                dtype = np.dtype(np.uint8)
            else:
                dtype = np.dtype(np.int16)

            self.assertIsInstance(grain.data, np.ndarray)
            self.assertEqual(grain.data.nbytes, width*height*bps + 2*(width*height*bps >> (hs + vs)))
            self.assertEqual(grain.data.dtype, dtype)
            self.assertEqual(grain.data.size, width*height + 2*(width*height >> (hs + vs)))
            self.assertEqual(grain.data.itemsize, bps)
            self.assertEqual(grain.data.ndim, 1)
            self.assertEqual(grain.data.shape, (width*height + 2*(width*height >> (hs + vs)),))

            self.assertEqual(repr(grain), "VideoGrain({!r},< numpy data of length {} >)".format(grain.meta, len(grain.data)))

            self.assertIsInstance(grain.components[0].data, np.ndarray)
            self.assertEqual(grain.components[0].data.nbytes, width*height*bps)
            self.assertEqual(grain.components[0].data.dtype, dtype)
            self.assertEqual(grain.components[0].data.size, width*height)
            self.assertEqual(grain.components[0].data.itemsize, bps)
            self.assertEqual(grain.components[0].data.ndim, 2)
            self.assertEqual(grain.components[0].data.shape, (width, height))

            self.assertIsInstance(grain.components[1].data, np.ndarray)
            self.assertEqual(grain.components[1].data.nbytes, width*height*bps >> (hs + vs))
            self.assertEqual(grain.components[1].data.dtype, dtype)
            self.assertEqual(grain.components[1].data.size, width*height >> (hs + vs))
            self.assertEqual(grain.components[1].data.itemsize, bps)
            self.assertEqual(grain.components[1].data.ndim, 2)
            self.assertEqual(grain.components[1].data.shape, (width >> hs, height >> vs))

            self.assertIsInstance(grain.components[2].data, np.ndarray)
            self.assertEqual(grain.components[2].data.nbytes, width*height*bps >> (hs + vs))
            self.assertEqual(grain.components[2].data.dtype, dtype)
            self.assertEqual(grain.components[2].data.size, width*height >> (hs + vs))
            self.assertEqual(grain.components[2].data.itemsize, bps)
            self.assertEqual(grain.components[2].data.ndim, 2)
            self.assertEqual(grain.components[2].data.shape, (width >> hs, height >> vs))

            self.assertEqual(grain.expected_length, (width*height + 2*(width >> hs)*(height >> vs))*bps)

            # Test that changes to the component arrays are reflected in the main data array
            for y in range(0, 16):
                for x in range(0, 16):
                    grain.components[0].data[x, y] = (y*width + x) & 0x3F

            for y in range(0, 16 >> vs):
                for x in range(0, 16 >> hs):
                    grain.components[1].data[x, y] = (y*(width >> hs) + x) & 0x3F + 0x40
                    grain.components[2].data[x, y] = (y*(width >> hs) + x) & 0x3F + 0x50

            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(grain.data[y*width + x], (y*width + x) & 0x3F)

            for y in range(0, 16 >> vs):
                for x in range(0, 16 >> hs):
                    self.assertEqual(grain.data[width*height + y*(width >> hs) + x], (y*(width >> hs) + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[width*height + (width >> hs)*(height >> vs) + y*(width >> hs) + x], (y*(width >> hs) + x) & 0x3F + 0x50)

        return __inner

    def test_video_grain_create(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        for fmt in [CogFrameFormat.S16_444_10BIT,
                    CogFrameFormat.S16_422_10BIT,
                    CogFrameFormat.S16_420_10BIT,
                    CogFrameFormat.S16_444_12BIT,
                    CogFrameFormat.S16_422_12BIT,
                    CogFrameFormat.S16_420_12BIT,
                    CogFrameFormat.S16_444,
                    CogFrameFormat.S16_422,
                    CogFrameFormat.S16_420,
                    CogFrameFormat.U8_444,
                    CogFrameFormat.U8_422,
                    CogFrameFormat.U8_420,
                    CogFrameFormat.U8_444_RGB,
                    CogFrameFormat.S16_444_RGB,
                    CogFrameFormat.S16_444_12BIT_RGB,
                    CogFrameFormat.S16_444_10BIT_RGB]:
            with self.subTest(fmt=fmt):
                with mock.patch.object(Timestamp, "get_time", return_value=cts):
                    grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                       cog_frame_format=fmt,
                                       width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

                self.assertIsVideoGrain(fmt)(grain)

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
