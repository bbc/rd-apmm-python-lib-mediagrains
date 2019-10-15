#!/usr/bin/python
#
# Copyright 2019 British Broadcasting Corporation
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

from __future__ import print_function
from __future__ import absolute_import

from unittest import TestCase
import uuid

from mediagrains import VideoGrain
from mediagrains.cogenums import CogFrameFormat
from mediagrains.comparison import compute_psnr

SRC_ID = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
FLOW_ID = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")


pixel_ranges = {
    CogFrameFormat.U8_444: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.U8_422: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.U8_420: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.S16_444_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_422_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_420_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_444_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_422_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_420_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_444: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
    CogFrameFormat.S16_422: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
    CogFrameFormat.S16_420: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
}


def set_colour_bars(vg, noise_mask=0xffff):
    """The code, except for the noise_mask, was copied from testsignalgenerator. It was duplicated here to keep
       the unit tests isolated.

    :params vg: A video GRAIN
    :params noise_mask: A mask applied to the colour bar line pixels
    """
    cog_frame_format = vg.format
    intensity = 0.75

    _bpp = pixel_ranges[cog_frame_format][0]
    _steps = 8
    bs = 16 - pixel_ranges[cog_frame_format][4]

    values = [
        (int((0xFFFF >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs),
        (int((0xE1FF >> bs) * intensity), 0x0000 >> bs, 0x9400 >> bs),
        (int((0xB200 >> bs) * intensity), 0xABFF >> bs, 0x0000 >> bs),
        (int((0x95FF >> bs) * intensity), 0x2BFF >> bs, 0x15FF >> bs),
        (int((0x69FF >> bs) * intensity), 0xD400 >> bs, 0xEA00 >> bs),
        (int((0x4C00 >> bs) * intensity), 0x5400 >> bs, 0xFFFF >> bs),
        (int((0x1DFF >> bs) * intensity), 0xFFFF >> bs, 0x6BFF >> bs),
        (int((0x0000 >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs)]

    lines = [bytearray(vg.components[0].width*_bpp), bytearray(vg.components[1].width*_bpp), bytearray(vg.components[2].width*_bpp)]
    for c in range(0, 3):
        for x in range(0, vg.components[c].width):
            pos = x//(vg.components[c].width//_steps)
            if _bpp == 1:
                lines[c][x] = values[pos][c] & noise_mask
            elif _bpp == 2:
                lines[c][2*x + 0] = ((values[pos][c] & noise_mask) & 0xFF)
                lines[c][2*x + 1] = ((values[pos][c] & noise_mask) >> 8) & 0xFF

    for c in range(0, 3):
        for y in range(0, vg.components[c].height):
            offset = vg.components[c].offset + y*vg.components[c].stride
            vg.data[offset:offset + vg.components[c].width*_bpp] = lines[c]


class TestPSNR(TestCase):
    def _check_psnr_range(self, computed, ranges, max_diff):
        for psnr, psnr_range in zip(computed, ranges):
            if psnr < psnr_range - max_diff or psnr > psnr_range + max_diff:
                return False
        return True

    def _create_grain(self, cog_frame_format):
        return VideoGrain(SRC_ID, FLOW_ID,
                          cog_frame_format=cog_frame_format,
                          width=480, height=270)

    def test_identical_data(self):
        grain = self._create_grain(CogFrameFormat.U8_422)
        set_colour_bars(grain, noise_mask=0xfa)

        self.assertEqual(compute_psnr(grain, grain), [float('Inf'), float('Inf'), float('Inf')])

    def test_planar_8bit(self):
        grain_a = self._create_grain(CogFrameFormat.U8_422)
        set_colour_bars(grain_a)
        grain_b = self._create_grain(CogFrameFormat.U8_422)
        set_colour_bars(grain_b, noise_mask=0xfffa)

        psnr = compute_psnr(grain_a, grain_b)
        self.assertTrue(self._check_psnr_range(psnr, [36.47984486113692, 39.45318336217709, 38.90095545159027], 0.1))

    def test_planar_10bit(self):
        grain_a = self._create_grain(CogFrameFormat.S16_422_10BIT)
        set_colour_bars(grain_a)
        grain_b = self._create_grain(CogFrameFormat.S16_422_10BIT)
        set_colour_bars(grain_b, noise_mask=0xfffa)

        psnr = compute_psnr(grain_a, grain_b)
        self.assertTrue(self._check_psnr_range(psnr, [48.8541475647564, 50.477799910245636, 50.477799910245636], 0.1))

    def test_planar_12bit(self):
        grain_a = self._create_grain(CogFrameFormat.S16_422_12BIT)
        set_colour_bars(grain_a)
        grain_b = self._create_grain(CogFrameFormat.S16_422_12BIT)
        set_colour_bars(grain_b, noise_mask=0xfffa)

        psnr = compute_psnr(grain_a, grain_b)
        self.assertTrue(self._check_psnr_range(psnr, [60.30687786176762, 62.525365357931186, 62.525365357931186], 0.1))

    def test_planar_16bit(self):
        grain_a = self._create_grain(CogFrameFormat.S16_422)
        set_colour_bars(grain_a)
        grain_b = self._create_grain(CogFrameFormat.S16_422)
        set_colour_bars(grain_b, noise_mask=0xfffa)

        psnr = compute_psnr(grain_a, grain_b)
        self.assertTrue(self._check_psnr_range(psnr, [84.39126581514387, 86.60975331130743, 86.60975331130743], 0.1))

    def test_compressed_unsupported(self):
        grain = self._create_grain(CogFrameFormat.H264)

        with self.assertRaises(NotImplementedError):
            compute_psnr(grain, grain)

    def test_packed_unsupported(self):
        grain = self._create_grain(CogFrameFormat.UYVY)

        with self.assertRaises(NotImplementedError):
            compute_psnr(grain, grain)
