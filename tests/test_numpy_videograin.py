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

from asynctest import TestCase, mock

import uuid
from mediagrains.numpy import VideoGrain, VIDEOGRAIN
from mediagrains.numpy.videograin import _dtype_from_cogframeformat
from mediagrains.cogenums import (
    CogFrameFormat,
    CogFrameLayout,
    COG_FRAME_FORMAT_BYTES_PER_VALUE,
    COG_FRAME_FORMAT_H_SHIFT,
    COG_FRAME_FORMAT_V_SHIFT,
    COG_FRAME_IS_PLANAR,
    COG_FRAME_IS_PLANAR_RGB,
    COG_FRAME_FORMAT_ACTIVE_BITS)
from mediagrains.gsf import loads, dumps
from mediagrains.comparison import compare_grain
from mediagrains import grain_constructors as bytesgrain_constructors
from mediatimestamp.immutable import Timestamp, TimeRange
from fractions import Fraction
from copy import copy, deepcopy
from typing import Tuple, Optional

from itertools import chain, repeat

import numpy as np


class ConvertibleToTimestamp (object):
    def __init__(self, ts: Timestamp):
        self.ts = ts

    def __mediatimestamp__(self) -> Timestamp:
        return self.ts


class TestGrain (TestCase):
    def _get_bitdepth(self, fmt):
        if COG_FRAME_IS_PLANAR(fmt):
            return COG_FRAME_FORMAT_ACTIVE_BITS(fmt)
        elif fmt in [CogFrameFormat.UYVY,
                     CogFrameFormat.YUYV,
                     CogFrameFormat.RGB,
                     CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.ARGB,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ABGR,
                     CogFrameFormat.xBGR]:
            return 8
        elif fmt == CogFrameFormat.v216:
            return 16
        elif fmt == CogFrameFormat.v210:
            return 10
        else:
            raise Exception()

    def _get_hs_vs_and_bps(self, fmt):
        if COG_FRAME_IS_PLANAR(fmt):
            return (COG_FRAME_FORMAT_H_SHIFT(fmt), COG_FRAME_FORMAT_V_SHIFT(fmt), COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt))
        elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
            return (1, 0, 1)
        elif fmt in [CogFrameFormat.RGB,
                     CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.ARGB,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ABGR,
                     CogFrameFormat.xBGR]:
            return (0, 0, 1)
        elif fmt == CogFrameFormat.v216:
            return (1, 0, 2)
        elif fmt == CogFrameFormat.v210:
            return (1, 0, 4)
        else:
            raise Exception()

    def _is_rgb(self, fmt):
        if COG_FRAME_IS_PLANAR(fmt):
            return COG_FRAME_IS_PLANAR_RGB(fmt)
        elif fmt in [CogFrameFormat.UYVY,
                     CogFrameFormat.YUYV,
                     CogFrameFormat.v216,
                     CogFrameFormat.v210]:
            return False
        elif fmt in [CogFrameFormat.RGB,
                     CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.ARGB,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ABGR,
                     CogFrameFormat.xBGR]:
            return True
        else:
            raise Exception()

    def assertComponentsAreModifiable(self, grain):
        width = grain.width
        height = grain.height
        fmt = grain.format

        (hs, vs, _) = self._get_hs_vs_and_bps(fmt)

        # Test that changes to the component arrays are reflected in the main data array
        for y in range(0, 16):
            for x in range(0, 16):
                grain.component_data[0][x, y] = (y*16 + x) & 0x3F

        for y in range(0, 16 >> vs):
            for x in range(0, 16 >> hs):
                grain.component_data[1][x, y] = (y*16 + x) & 0x3F + 0x40
                grain.component_data[2][x, y] = (y*16 + x) & 0x3F + 0x50

        if COG_FRAME_IS_PLANAR(fmt):
            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(grain.data[y*width + x], (y*16 + x) & 0x3F)

            for y in range(0, 16 >> vs):
                for x in range(0, 16 >> hs):
                    self.assertEqual(grain.data[width*height + y*(width >> hs) + x], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[width*height + (width >> hs)*(height >> vs) + y*(width >> hs) + x], (y*16 + x) & 0x3F + 0x50)

        elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.v216]:
            for y in range(0, 16):
                for x in range(0, 8):
                    self.assertEqual(grain.data[y*width*2 + 4*x + 0], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 1], (y*16 + 2*x + 0) & 0x3F)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 2], (y*16 + x) & 0x3F + 0x50)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 3], (y*16 + 2*x + 1) & 0x3F)

        elif fmt == CogFrameFormat.YUYV:
            for y in range(0, 16):
                for x in range(0, 8):
                    self.assertEqual(grain.data[y*width*2 + 4*x + 0], (y*16 + 2*x + 0) & 0x3F)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 1], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 2], (y*16 + 2*x + 1) & 0x3F)
                    self.assertEqual(grain.data[y*width*2 + 4*x + 3], (y*16 + x) & 0x3F + 0x50)

        elif fmt == CogFrameFormat.RGB:
            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(grain.data[y*width*3 + 3*x + 0], (y*16 + x) & 0x3F)
                    self.assertEqual(grain.data[y*width*3 + 3*x + 1], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[y*width*3 + 3*x + 2], (y*16 + x) & 0x3F + 0x50)

        elif fmt in [CogFrameFormat.RGBx,
                     CogFrameFormat.RGBA,
                     CogFrameFormat.BGRx,
                     CogFrameFormat.BGRx]:
            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(grain.data[y*width*4 + 4*x + 0], (y*16 + x) & 0x3F)
                    self.assertEqual(grain.data[y*width*4 + 4*x + 1], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[y*width*4 + 4*x + 2], (y*16 + x) & 0x3F + 0x50)

        elif fmt in [CogFrameFormat.ARGB,
                     CogFrameFormat.xRGB,
                     CogFrameFormat.ABGR,
                     CogFrameFormat.xBGR]:
            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(grain.data[y*width*4 + 4*x + 1], (y*16 + x) & 0x3F)
                    self.assertEqual(grain.data[y*width*4 + 4*x + 2], (y*16 + x) & 0x3F + 0x40)
                    self.assertEqual(grain.data[y*width*4 + 4*x + 3], (y*16 + x) & 0x3F + 0x50)

        else:
            raise Exception()

    def assertIsVideoGrain(self,
                           fmt,
                           src_id=uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429"),
                           flow_id=uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb"),
                           ots=Timestamp.from_tai_sec_nsec("417798915:5"),
                           sts=Timestamp.from_tai_sec_nsec("417798915:10"),
                           cts=Timestamp.from_tai_sec_nsec("417798915:0"),
                           rate=Fraction(25, 1),
                           width=1920,
                           height=1080,
                           ignore_cts=False):
        def __inner(grain):
            self.assertEqual(grain.grain_type, "video")
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ots)
            self.assertEqual(grain.final_origin_timestamp(), ots)
            self.assertEqual(grain.origin_timerange(), TimeRange.from_single_timestamp(ots))
            self.assertEqual(grain.sync_timestamp, sts)
            if not ignore_cts:
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

            (hs, vs, bps) = self._get_hs_vs_and_bps(fmt)

            if COG_FRAME_IS_PLANAR(fmt):
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

                self.assertEqual(grain.expected_length, (width*height + 2*(width >> hs)*(height >> vs))*bps)
            elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
                self.assertEqual(len(grain.components), 1)
                self.assertEqual(grain.components[0].stride, width*bps + 2*(width >> hs)*bps)
                self.assertEqual(grain.components[0].width, width)
                self.assertEqual(grain.components[0].height, height)
                self.assertEqual(grain.components[0].offset, 0)
                self.assertEqual(grain.components[0].length, width*height*bps*2)
                self.assertEqual(len(grain.components[0]), 5)

                self.assertEqual(grain.expected_length, width*height*bps*2)
            elif fmt in [CogFrameFormat.RGB]:
                self.assertEqual(len(grain.components), 1)
                self.assertEqual(grain.components[0].stride, 3*width*bps)
                self.assertEqual(grain.components[0].width, width)
                self.assertEqual(grain.components[0].height, height)
                self.assertEqual(grain.components[0].offset, 0)
                self.assertEqual(grain.components[0].length, width*height*bps*3)
                self.assertEqual(len(grain.components[0]), 5)
            elif fmt in [CogFrameFormat.RGBx,
                         CogFrameFormat.RGBA,
                         CogFrameFormat.BGRx,
                         CogFrameFormat.BGRx,
                         CogFrameFormat.ARGB,
                         CogFrameFormat.xRGB,
                         CogFrameFormat.ABGR,
                         CogFrameFormat.xBGR]:
                self.assertEqual(len(grain.components), 1)
                self.assertEqual(grain.components[0].stride, 4*width*bps)
                self.assertEqual(grain.components[0].width, width)
                self.assertEqual(grain.components[0].height, height)
                self.assertEqual(grain.components[0].offset, 0)
                self.assertEqual(grain.components[0].length, width*height*bps*4)
                self.assertEqual(len(grain.components[0]), 5)

            elif fmt == CogFrameFormat.v216:
                self.assertEqual(len(grain.components), 1)
                self.assertEqual(grain.components[0].stride, 2*width*bps)
                self.assertEqual(grain.components[0].width, width)
                self.assertEqual(grain.components[0].height, height)
                self.assertEqual(grain.components[0].offset, 0)
                self.assertEqual(grain.components[0].length, width*height*bps*2)
                self.assertEqual(len(grain.components[0]), 5)

            elif fmt == CogFrameFormat.v210:
                self.assertEqual(len(grain.components), 1)
                self.assertEqual(grain.components[0].stride, (((width + 47) // 48) * 128))
                self.assertEqual(grain.components[0].width, width)
                self.assertEqual(grain.components[0].height, height)
                self.assertEqual(grain.components[0].offset, 0)
                self.assertEqual(grain.components[0].length, height*(((width + 47) // 48) * 128))
                self.assertEqual(len(grain.components[0]), 5)

            else:
                raise Exception()

            if bps == 1:
                dtype = np.dtype(np.uint8)
            elif bps == 2:
                dtype = np.dtype(np.uint16)
            elif bps == 4:
                dtype = np.dtype(np.uint32)
            else:
                raise Exception()

            self.assertIsInstance(grain.data, np.ndarray)
            self.assertEqual(grain.data.nbytes, grain.expected_length)
            self.assertEqual(grain.data.dtype, dtype)
            self.assertEqual(grain.data.size, grain.expected_length//bps)
            self.assertEqual(grain.data.itemsize, bps)
            self.assertEqual(grain.data.ndim, 1)
            self.assertEqual(grain.data.shape, (grain.expected_length//bps,))

            self.assertEqual(repr(grain), "VideoGrain({!r},< numpy data of length {} >)".format(grain.meta, len(grain.data)))

            if fmt == CogFrameFormat.v210:
                # V210 is barely supported. Convert it to something else to actually use it!
                self.assertEqual(len(grain.component_data), 0)
            else:
                self.assertIsInstance(grain.component_data[0], np.ndarray)
                self.assertTrue(np.array_equal(grain.component_data[0].nbytes, width*height*bps))
                self.assertTrue(np.array_equal(grain.component_data[0].dtype, dtype))
                self.assertTrue(np.array_equal(grain.component_data[0].size, width*height))
                self.assertTrue(np.array_equal(grain.component_data[0].itemsize, bps))
                self.assertTrue(np.array_equal(grain.component_data[0].ndim, 2))
                self.assertTrue(np.array_equal(grain.component_data[0].shape, (width, height)))

                self.assertIsInstance(grain.component_data[1], np.ndarray)
                self.assertTrue(np.array_equal(grain.component_data[1].nbytes, width*height*bps >> (hs + vs)))
                self.assertTrue(np.array_equal(grain.component_data[1].dtype, dtype))
                self.assertTrue(np.array_equal(grain.component_data[1].size, width*height >> (hs + vs)))
                self.assertTrue(np.array_equal(grain.component_data[1].itemsize, bps))
                self.assertTrue(np.array_equal(grain.component_data[1].ndim, 2))
                self.assertTrue(np.array_equal(grain.component_data[1].shape, (width >> hs, height >> vs)))

                self.assertIsInstance(grain.component_data[2], np.ndarray)
                self.assertTrue(np.array_equal(grain.component_data[2].nbytes, width*height*bps >> (hs + vs)))
                self.assertTrue(np.array_equal(grain.component_data[2].dtype, dtype))
                self.assertTrue(np.array_equal(grain.component_data[2].size, width*height >> (hs + vs)))
                self.assertTrue(np.array_equal(grain.component_data[2].itemsize, bps))
                self.assertTrue(np.array_equal(grain.component_data[2].ndim, 2))
                self.assertTrue(np.array_equal(grain.component_data[2].shape, (width >> hs, height >> vs)))

        return __inner

    def _test_pattern_rgb(self, fmt: CogFrameFormat) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return a 16x16 pixel RGB test pattern"""
        bd = self._get_bitdepth(fmt)

        v = (1 << (bd - 2))*3
        return (np.array([[v, v, v, v, 0, 0, 0, 0, v, v, v, v, 0, 0, 0, 0] for _ in range(0, 16)], dtype=_dtype_from_cogframeformat(fmt)).transpose(),
                np.array([[v, v, v, v, v, v, v, v, 0, 0, 0, 0, 0, 0, 0, 0] for _ in range(0, 16)], dtype=_dtype_from_cogframeformat(fmt)).transpose(),
                np.array([[v, v, 0, 0, v, v, 0, 0, v, v, 0, 0, v, v, 0, 0] for _ in range(0, 16)], dtype=_dtype_from_cogframeformat(fmt)).transpose())

    def _test_pattern_yuv(self, fmt: CogFrameFormat) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        (R, G, B) = self._test_pattern_rgb(fmt)
        (R, G, B) = (R.astype(np.dtype(np.double)),
                     G.astype(np.dtype(np.double)),
                     B.astype(np.dtype(np.double)))
        bd = self._get_bitdepth(fmt)
        (hs, vs, _) = self._get_hs_vs_and_bps(fmt)

        Y = (R*0.2126 + G*0.7152 + B*0.0722)
        U = (R*-0.114572 - G*0.385428 + B*0.5 + (1 << (bd - 1)))
        V = (R*0.5 - G*0.454153 - B*0.045847 + (1 << (bd - 1)))

        if hs == 1:
            U = (U[0::2, :] + U[1::2, :])/2
            V = (V[0::2, :] + V[1::2, :])/2
        if vs == 1:
            U = (U[:, 0::2] + U[:, 1::2])/2
            V = (V[:, 0::2] + V[:, 1::2])/2

        return (np.around(Y).astype(_dtype_from_cogframeformat(fmt)),
                np.around(U).astype(_dtype_from_cogframeformat(fmt)),
                np.around(V).astype(_dtype_from_cogframeformat(fmt)))

    def _test_pattern_v210(self) -> np.ndarray:
        (Y, U, V) = self._test_pattern_yuv(CogFrameFormat.S16_422_10BIT)

        output = np.zeros(32*16, dtype=np.dtype(np.uint32))
        for y in range(0, 16):

            yy = chain(iter(Y[:, y]), repeat(0))
            uu = chain(iter(U[:, y]), repeat(0))
            vv = chain(iter(V[:, y]), repeat(0))

            for x in range(0, 8):
                output[y*32 + 4*x + 0] = next(uu) | (next(yy) << 10) | (next(vv) << 20)
                output[y*32 + 4*x + 1] = next(yy) | (next(uu) << 10) | (next(yy) << 20)
                output[y*32 + 4*x + 2] = next(vv) | (next(yy) << 10) | (next(uu) << 20)
                output[y*32 + 4*x + 3] = next(yy) | (next(vv) << 10) | (next(yy) << 20)

        return output

    def write_test_pattern(self, grain):
        fmt = grain.format

        if self._is_rgb(fmt):
            (R, G, B) = self._test_pattern_rgb(fmt)

            grain.component_data.R[:, :] = R
            grain.component_data.G[:, :] = G
            grain.component_data.B[:, :] = B
        elif fmt == CogFrameFormat.v210:
            grain.data[:] = self._test_pattern_v210()
        else:
            (Y, U, V) = self._test_pattern_yuv(fmt)

            grain.component_data.Y[:, :] = Y
            grain.component_data.U[:, :] = U
            grain.component_data.V[:, :] = V

    def assertArrayEqual(self, a: np.ndarray, b: np.ndarray, max_diff: Optional[int] = None):
        if max_diff is None:
            self.assertTrue(np.array_equal(a, b), msg="{} != {}".format(a, b))
        else:
            a = a.astype(np.dtype(np.int64))
            b = b.astype(np.dtype(np.int64))
            self.assertTrue(np.amax(np.absolute(a - b)) <= max_diff,
                            msg="{} - {} = {} (allowing up to {} difference)".format(a, b, a - b, max_diff))

    def assertMatchesTestPattern(self, grain: VIDEOGRAIN, max_diff: Optional[int] = None):
        fmt = grain.format

        if self._is_rgb(fmt):
            (R, G, B) = self._test_pattern_rgb(fmt)

            self.assertArrayEqual(grain.component_data.R[:, :], R, max_diff=max_diff)
            self.assertArrayEqual(grain.component_data.G[:, :], G, max_diff=max_diff)
            self.assertArrayEqual(grain.component_data.B[:, :], B, max_diff=max_diff)
        elif fmt == CogFrameFormat.v210:
            self.assertArrayEqual(grain.data, self._test_pattern_v210())
        else:
            (Y, U, V) = self._test_pattern_yuv(fmt)

            self.assertArrayEqual(grain.component_data.Y[:, :], Y, max_diff=max_diff)
            self.assertArrayEqual(grain.component_data.U[:, :], U, max_diff=max_diff)
            self.assertArrayEqual(grain.component_data.V[:, :], V, max_diff=max_diff)

    def test_video_grain_create(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        for fmt in [CogFrameFormat.S32_444,
                    CogFrameFormat.S32_422,
                    CogFrameFormat.S32_420,
                    CogFrameFormat.S16_444_10BIT,
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
                    CogFrameFormat.S16_444_10BIT_RGB,
                    CogFrameFormat.UYVY,
                    CogFrameFormat.YUYV,
                    CogFrameFormat.RGB,
                    CogFrameFormat.RGBx,
                    CogFrameFormat.RGBA,
                    CogFrameFormat.BGRx,
                    CogFrameFormat.BGRx,
                    CogFrameFormat.ARGB,
                    CogFrameFormat.xRGB,
                    CogFrameFormat.ABGR,
                    CogFrameFormat.xBGR,
                    CogFrameFormat.v216,
                    CogFrameFormat.v210]:
            with self.subTest(fmt=fmt):
                with mock.patch.object(Timestamp, "get_time", return_value=cts):
                    grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                       cog_frame_format=fmt,
                                       width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

                self.assertIsVideoGrain(fmt)(grain)

                if fmt is not CogFrameFormat.v210:
                    self.assertComponentsAreModifiable(grain)

    def test_video_grain_create_with_convertible_timestamp(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id,
                               origin_timestamp=ConvertibleToTimestamp(ots),
                               sync_timestamp=ConvertibleToTimestamp(sts),
                               cog_frame_format=CogFrameFormat.S16_422_10BIT,
                               width=1920, height=1080, cog_frame_layout=CogFrameLayout.FULL_FRAME)

        self.assertIsVideoGrain(CogFrameFormat.S16_422_10BIT)(grain)
        self.assertComponentsAreModifiable(grain)

    async def test_video_grain_async_create(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        async def _get_data():
            _data = bytearray(16*16*3)
            for i in range(0, 3):
                for y in range(0, 16):
                    for x in range(0, 16):
                        _data[(i*16 + y)*16 + x] = x + (y << 4)
            return _data

        data_awaitable = _get_data()

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                               cog_frame_format=CogFrameFormat.U8_444,
                               width=16, height=16, cog_frame_layout=CogFrameLayout.FULL_FRAME,
                               data=data_awaitable)

        self.assertIsNone(grain.data)
        self.assertEqual(len(grain.component_data), 0)

        async with grain as _grain:
            for y in range(0, 16):
                for x in range(0, 16):
                    self.assertEqual(_grain.component_data.Y[x, y], x + (y << 4))
                    self.assertEqual(_grain.component_data.U[x, y], x + (y << 4))
                    self.assertEqual(_grain.component_data.V[x, y], x + (y << 4))

    def test_video_grain_convert(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        def pairs_from(fmts):
            for fmt_in in fmts:
                for fmt_out in fmts:
                    yield (fmt_in, fmt_out)

        fmts = [CogFrameFormat.YUYV, CogFrameFormat.UYVY, CogFrameFormat.U8_444, CogFrameFormat.U8_422, CogFrameFormat.U8_420,  # All YUV 8bit formats
                CogFrameFormat.RGB, CogFrameFormat.U8_444_RGB, CogFrameFormat.RGBx, CogFrameFormat.xRGB, CogFrameFormat.BGRx, CogFrameFormat.xBGR,
                # All 8-bit 3 component RGB formats
                CogFrameFormat.v216, CogFrameFormat.S16_444, CogFrameFormat.S16_422, CogFrameFormat.S16_420,  # All YUV 16bit formats
                CogFrameFormat.S16_444_10BIT, CogFrameFormat.S16_422_10BIT, CogFrameFormat.S16_420_10BIT,  # All YUV 10bit formats except for v210
                CogFrameFormat.v210,  # v210, may the gods be merciful to us for including it
                CogFrameFormat.S16_444_12BIT, CogFrameFormat.S16_422_12BIT, CogFrameFormat.S16_420_12BIT,  # All YUV 12bit formats
                CogFrameFormat.S32_444, CogFrameFormat.S32_422, CogFrameFormat.S32_420,  # All YUV 32bit formats
                CogFrameFormat.S16_444_RGB, CogFrameFormat.S16_444_10BIT_RGB, CogFrameFormat.S16_444_12BIT_RGB, CogFrameFormat.S32_444_RGB]  # Other planar RGB
        for (fmt_in, fmt_out) in pairs_from(fmts):
            with self.subTest(fmt_in=fmt_in, fmt_out=fmt_out):
                with mock.patch.object(Timestamp, "get_time", return_value=cts):
                    grain_in = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                          cog_frame_format=fmt_in,
                                          width=16, height=16, cog_frame_layout=CogFrameLayout.FULL_FRAME)

                self.assertIsVideoGrain(fmt_in, width=16, height=16)(grain_in)
                self.write_test_pattern(grain_in)

                grain_out = grain_in.convert(fmt_out)

                if fmt_in != fmt_out:
                    flow_id_out = grain_in.flow_id_for_converted_flow(fmt_out)
                else:
                    flow_id_out = flow_id
                self.assertIsVideoGrain(fmt_out, flow_id=flow_id_out, width=16, height=16, ignore_cts=True)(grain_out)

                # Some conversions for v210 are just really hard to check when not exact
                # For other formats it's simpler
                if fmt_out != CogFrameFormat.v210:
                    # We have several possible cases here:
                    # * We've changed bit-depth
                    # * We've changed colour subsampling
                    # * We've changed colourspace
                    #
                    # In addition we have have done none of those things, or even more than one

                    # If we've increased bit-depth there will be rounding errors
                    if self._get_bitdepth(fmt_out) > self._get_bitdepth(fmt_in):
                        self.assertMatchesTestPattern(grain_out, max_diff=1 << (self._get_bitdepth(fmt_out) + 2 - self._get_bitdepth(fmt_in)))

                    # If we're changing from yuv to rgb then there's some potential for floating point errors, depending on the sizes
                    elif self._get_bitdepth(fmt_in) >= 16 and not self._is_rgb(fmt_in) and fmt_out == CogFrameFormat.S16_444_RGB:
                        self.assertMatchesTestPattern(grain_out, max_diff=2)
                    elif self._get_bitdepth(fmt_in) == 32 and not self._is_rgb(fmt_in) and fmt_out == CogFrameFormat.S32_444_RGB:
                        self.assertMatchesTestPattern(grain_out, max_diff=1 << 10)  # The potential errors in 32 bit conversions are very large

                    # If we've decreased bit-depth *and* or changed from rgb to yuv then there is a smaller scope for error
                    elif ((self._get_bitdepth(fmt_out) < self._get_bitdepth(fmt_in)) or
                            (self._is_rgb(fmt_in) != self._is_rgb(fmt_out))):
                        self.assertMatchesTestPattern(grain_out, max_diff=1)

                    # If we're in none of these cases then the transformation should be lossless
                    else:
                        self.assertMatchesTestPattern(grain_out)
                else:
                    grain_rev = grain_out.convert(fmt_in)

                    # The conversion from 10-bit 422 should be lossless
                    if fmt_in in [CogFrameFormat.v210, CogFrameFormat.S16_422_10BIT]:
                        self.assertMatchesTestPattern(grain_rev)

                    # If we are not colour space converting and our input bit-depth is equal or lower to 10bits we have minor scope for rounding error
                    elif self._get_bitdepth(fmt_in) in [8, 10] and not self._is_rgb(fmt_in):
                        self.assertMatchesTestPattern(grain_rev, max_diff=1)

                    # If we are significantly lowering the bit depth then there is potential for significant error when reversing the process
                    elif self._get_bitdepth(fmt_in) in [12, 16, 32] and not self._is_rgb(fmt_in):
                        self.assertMatchesTestPattern(grain_rev, max_diff=1 << (self._get_bitdepth(fmt_in) - 9))

                    # And even more if we are also colour converting
                    elif self._get_bitdepth(fmt_in) in [12, 16, 32] and self._is_rgb(fmt_in):
                        self.assertMatchesTestPattern(grain_rev, max_diff=1 << (self._get_bitdepth(fmt_in) - 8))

                    # Otherwise if we are only colour converting then the potential error is a small floating point rounding error
                    elif self._is_rgb(fmt_in):
                        self.assertMatchesTestPattern(grain_rev, max_diff=4)

    def test_video_grain_create_discontiguous(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        data = bytearray(11*1024*1024)

        grain = VideoGrain({
            "grain": {
                "grain_type": "video",
                "source_id": src_id,
                "flow_id": flow_id,
                "origin_timestamp": ots,
                "sync_timestamp": sts,
                "creation_timestamp": cts,
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
                            "stride": 4096,
                            "width": 1920,
                            "height": 1080,
                            "length": 4423680,
                            "offset": 0
                        },
                        {
                            "stride": 2048,
                            "width": 960,
                            "height": 1080,
                            "length": 2211840,
                            "offset": 5*1024*1024
                        },
                        {
                            "stride": 2048,
                            "width": 960,
                            "height": 1080,
                            "length": 2211840,
                            "offset": 8*1024*1024
                        },
                    ]
                }
            }
        }, data)

        for y in range(0, 16):
            for x in range(0, 16):
                grain.component_data[0][x, y] = (y*16 + x) & 0x3F

        for y in range(0, 16):
            for x in range(0, 8):
                grain.component_data[1][x, y] = (y*16 + x) & 0x3F + 0x40
                grain.component_data[2][x, y] = (y*16 + x) & 0x3F + 0x50

        for y in range(0, 16):
            for x in range(0, 16):
                self.assertEqual(grain.data[y*grain.components[0].stride//2 + x], (y*16 + x) & 0x3F)

        for y in range(0, 16):
            for x in range(0, 8):
                self.assertEqual(grain.data[grain.components[1].offset//2 + y*grain.components[1].stride//2 + x], (y*16 + x) & 0x3F + 0x40)
                self.assertEqual(grain.data[grain.components[2].offset//2 + y*grain.components[2].stride//2 + x], (y*16 + x) & 0x3F + 0x50)

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

    def test_length(self):
        """Check that the length override provides the length in bytes"""
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = bytesgrain_constructors.VideoGrain(src_id, flow_id,
                                                       cog_frame_format=CogFrameFormat.S16_422_10BIT,
                                                       width=480, height=270)
            np_grain = VideoGrain(grain).convert(CogFrameFormat.v210)

        self.assertEqual(np_grain.length, (480+47)//48*128*270)

    def test_video_grain_gsf_encode_decode(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        for fmt in [CogFrameFormat.S32_444,
                    CogFrameFormat.S32_422,
                    CogFrameFormat.S32_420,
                    CogFrameFormat.S16_444_10BIT,
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
                    CogFrameFormat.S16_444_10BIT_RGB,
                    CogFrameFormat.UYVY,
                    CogFrameFormat.YUYV,
                    CogFrameFormat.RGB,
                    CogFrameFormat.RGBx,
                    CogFrameFormat.RGBA,
                    CogFrameFormat.BGRx,
                    CogFrameFormat.BGRx,
                    CogFrameFormat.ARGB,
                    CogFrameFormat.xRGB,
                    CogFrameFormat.ABGR,
                    CogFrameFormat.xBGR,
                    CogFrameFormat.v216,
                    CogFrameFormat.v210]:
            with self.subTest(fmt=fmt):
                with mock.patch.object(Timestamp, "get_time", return_value=cts):
                    grain = VideoGrain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts,
                                       cog_frame_format=fmt,
                                       width=16, height=16, cog_frame_layout=CogFrameLayout.FULL_FRAME)

                self.write_test_pattern(grain)

                (head, segments) = loads(dumps([grain]))

                self.assertEqual(len(segments), 1)
                self.assertIn(1, segments)
                self.assertEqual(len(segments[1]), 1)

                new_grain = VideoGrain(segments[1][0])
                comp = compare_grain(new_grain, grain)
                self.assertTrue(comp, msg=str(comp))
