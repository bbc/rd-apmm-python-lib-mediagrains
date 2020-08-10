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

from asynctest import TestCase
from sys import version_info
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


def _create_grain(cog_frame_format):
    return VideoGrain(SRC_ID, FLOW_ID,
                      cog_frame_format=cog_frame_format,
                      width=480, height=270)


def _set_colour_bars(vg, noise_mask=0xffff):
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


def _convert_u8_uyvy(grain_u8):
    grain_uyvy = _create_grain(CogFrameFormat.UYVY)
    for y in range(0, grain_u8.height):
        for x in range(0, grain_u8.width//2):
            # U
            grain_uyvy.data[y*grain_uyvy.components[0].stride + 4*x + 0] = grain_u8.data[grain_u8.components[1].offset +
                                                                                         y*grain_u8.components[1].stride +
                                                                                         x]
            # Y
            grain_uyvy.data[y*grain_uyvy.components[0].stride + 4*x + 1] = grain_u8.data[grain_u8.components[0].offset +
                                                                                         y*grain_u8.components[0].stride +
                                                                                         2*x + 0]
            # V
            grain_uyvy.data[y*grain_uyvy.components[0].stride + 4*x + 2] = grain_u8.data[grain_u8.components[2].offset +
                                                                                         y*grain_u8.components[2].stride +
                                                                                         x]
            # Y
            grain_uyvy.data[y*grain_uyvy.components[0].stride + 4*x + 3] = grain_u8.data[grain_u8.components[0].offset +
                                                                                         y*grain_u8.components[0].stride +
                                                                                         2*x + 1]

    return grain_uyvy


class TestPSNR(TestCase):
    def _check_psnr_range(self, computed, ranges, max_diff):
        for psnr, psnr_range in zip(computed, ranges):
            if psnr < psnr_range - max_diff or psnr > psnr_range + max_diff:
                return False
        return True

    def _test_planar_format(self, cog_frame_format, expected):
        grain_a = _create_grain(cog_frame_format)
        _set_colour_bars(grain_a)
        grain_b = _create_grain(cog_frame_format)
        _set_colour_bars(grain_b, noise_mask=0xfffa)

        psnr = compute_psnr(grain_a, grain_b)
        self.assertTrue(self._check_psnr_range(psnr, expected, 0.1), "{} != {}".format(psnr, expected))

    def test_identical_data(self):
        grain = _create_grain(CogFrameFormat.U8_422)
        _set_colour_bars(grain, noise_mask=0xfa)

        self.assertEqual(compute_psnr(grain, grain), [float('Inf'), float('Inf'), float('Inf')])

    def test_planar_8bit(self):
        self._test_planar_format(CogFrameFormat.U8_422, [36.47984486113692, 39.45318336217709, 38.90095545159027])

    def test_planar_10bit(self):
        self._test_planar_format(CogFrameFormat.S16_422_10BIT, [48.8541475647564, 50.477799910245636, 50.477799910245636])

    def test_planar_12bit(self):
        self._test_planar_format(CogFrameFormat.S16_422_12BIT, [60.30687786176762, 62.525365357931186, 62.525365357931186])

    def test_planar_16bit(self):
        self._test_planar_format(CogFrameFormat.S16_422, [84.39126581514387, 86.60975331130743, 86.60975331130743])

    def test_uyvy_format(self):
        planar_grain_a = _create_grain(CogFrameFormat.U8_422)
        _set_colour_bars(planar_grain_a)
        grain_a = _convert_u8_uyvy(planar_grain_a)

        planar_grain_b = _create_grain(CogFrameFormat.U8_422)
        _set_colour_bars(planar_grain_b, noise_mask=0xfffa)
        grain_b = _convert_u8_uyvy(planar_grain_b)

        if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
            psnr = compute_psnr(grain_a, grain_b)
            expected = [36.47984486113692, 39.45318336217709, 38.90095545159027]
            self.assertTrue(self._check_psnr_range(psnr, expected, 0.1),
                            "{} != {}".format(psnr, expected))
        else:
            with self.assertRaises(NotImplementedError):
                compute_psnr(grain_a, grain_b)

    def test_mixed_format(self):
        grain_a = _create_grain(CogFrameFormat.U8_422)
        _set_colour_bars(grain_a)

        planar_grain_b = _create_grain(CogFrameFormat.U8_422)
        _set_colour_bars(planar_grain_b, noise_mask=0xfffa)
        grain_b = _convert_u8_uyvy(planar_grain_b)

        if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
            psnr = compute_psnr(grain_a, grain_b)
            expected = [36.47984486113692, 39.45318336217709, 38.90095545159027]
            self.assertTrue(self._check_psnr_range(psnr, expected, 0.1),
                            "{} != {}".format(psnr, expected))
        else:
            with self.assertRaises(NotImplementedError):
                compute_psnr(grain_a, grain_b)

    def test_compressed_unsupported(self):
        grain = _create_grain(CogFrameFormat.H264)

        with self.assertRaises(NotImplementedError):
            compute_psnr(grain, grain)
