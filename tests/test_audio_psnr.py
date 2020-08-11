# Copyright 2020 British Broadcasting Corporation
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
from fractions import Fraction
import math

from mediagrains.grain_constructors import AudioGrain as bytes_AudioGrain
from mediagrains.cogenums import (
    CogAudioFormat,
    COG_AUDIO_FORMAT_DEPTH,
    COG_AUDIO_FORMAT_DEPTH_S16,
    COG_AUDIO_FORMAT_DEPTH_S24,
    COG_AUDIO_FORMAT_DEPTH_S32,
    COG_AUDIO_IS_FLOAT,
    COG_AUDIO_IS_DOUBLE
)
from mediagrains.comparison import compare_grain, compute_psnr
from mediagrains.comparison.options import PSNR as PSNR_option

from audio_utils import construct_audio_grain_data

PCM_FORMATS = [
    CogAudioFormat.S16_PLANES,
    CogAudioFormat.S16_PAIRS,
    CogAudioFormat.S16_INTERLEAVED,
    CogAudioFormat.S24_PLANES,
    CogAudioFormat.S24_PAIRS,
    CogAudioFormat.S24_INTERLEAVED,
    CogAudioFormat.S32_PLANES,
    CogAudioFormat.S32_PAIRS,
    CogAudioFormat.S32_INTERLEAVED,
    CogAudioFormat.FLOAT_PLANES,
    CogAudioFormat.FLOAT_PAIRS,
    CogAudioFormat.FLOAT_INTERLEAVED,
    CogAudioFormat.DOUBLE_PLANES,
    CogAudioFormat.DOUBLE_PAIRS,
    CogAudioFormat.DOUBLE_INTERLEAVED
]


class TestPSNR (TestCase):
    def _min_max_val(self, fmt):
        if COG_AUDIO_IS_FLOAT(fmt) or COG_AUDIO_IS_DOUBLE(fmt):
            min_val = -1.0
            max_val = 1.0
        elif COG_AUDIO_FORMAT_DEPTH(fmt) == COG_AUDIO_FORMAT_DEPTH_S16:
            min_val = - (2 ** 15)
            max_val = 2 ** 15 - 1
        elif COG_AUDIO_FORMAT_DEPTH(fmt) == COG_AUDIO_FORMAT_DEPTH_S24:
            min_val = - (2 ** 23)
            max_val = 2 ** 23 - 1
        elif COG_AUDIO_FORMAT_DEPTH(fmt) == COG_AUDIO_FORMAT_DEPTH_S32:
            min_val = - (2 ** 31)
            max_val = 2 ** 31 - 1

        return (min_val, max_val)

    def _create_test_data(self, fmt, channels):
        """Create integer samples for each channel that covers the range extents"""
        if COG_AUDIO_IS_FLOAT(fmt) or COG_AUDIO_IS_DOUBLE(fmt):
            # Use 32-bit integer range and divide below to give [-1.0, 1.0] range
            (min_val, max_val) = self._min_max_val(CogAudioFormat.S32_INTERLEAVED)
        else:
            (min_val, max_val) = self._min_max_val(fmt)
        data = [[min_val, -512, -1, c, 1, 512, max_val] for c in range(channels)]

        if COG_AUDIO_IS_FLOAT(fmt) or COG_AUDIO_IS_DOUBLE(fmt):
            data = [[float(sample)/max_val for sample in chan_data] for chan_data in data]

        return data

    def _create_audio_grain(self, fmt, test_data, constructor=bytes_AudioGrain, grain_data=None):
        """Create a numpy AudioGrain from the test data"""
        if grain_data is None:
            grain_data = construct_audio_grain_data(fmt, test_data)
        channels = len(test_data)
        samples = len(test_data[0])
        return constructor(
            src_id=uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429"),
            flow_id=uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb"),
            rate=Fraction(48000, samples),
            cog_audio_format=fmt,
            samples=samples,
            channels=channels,
            sample_rate=48000,
            data=grain_data
        )

    def test_identical_compute_psnr(self):
        """Test that identical data produces 'inf' PSNR using the compute_psnr function"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    grain_a = self._create_audio_grain(fmt, test_data)
                    grain_b = bytes_AudioGrain(grain_a.meta, grain_a.data)

                    result = compute_psnr(grain_a, grain_b)
                    self.assertEqual(len(result), channels)
                    self.assertEqual(result, [float('Inf')] * channels)

    def test_identical__compare_grain(self):
        """Test that identical data produces 'inf' PSNR using the compare_grain function"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    grain_a = self._create_audio_grain(fmt, test_data)
                    grain_b = bytes_AudioGrain(grain_a.meta, grain_a.data)
                    result = compare_grain(
                        grain_a,
                        grain_b,
                        PSNR_option.data >= [float('Inf')] * channels
                    )
                    self.assertTrue(result)

    def test_diff(self):
        """Test that different data produces expected PSNR"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data_a = self._create_test_data(fmt, channels)
                    grain_a = self._create_audio_grain(fmt, test_data_a)

                    # Half the sample values for grain b
                    test_data_b = self._create_test_data(fmt, channels)
                    samples = len(test_data_b[0])
                    for c in range(channels):
                        for s in range(samples):
                            if COG_AUDIO_IS_FLOAT(fmt) or COG_AUDIO_IS_DOUBLE(fmt):
                                test_data_b[c][s] /= 2.0
                            else:
                                test_data_b[c][s] //= 2
                    grain_b = self._create_audio_grain(fmt, test_data_b)

                    # Calculate upper and lower bounds based on test data including 2 extremes and
                    # the rest of the samples near zero
                    (min_val, _) = self._min_max_val(fmt)
                    if COG_AUDIO_IS_FLOAT(fmt) or COG_AUDIO_IS_DOUBLE(fmt):
                        max_error = min_val / 2.0
                    else:
                        max_error = min_val // 2
                    samples = len(test_data_a[0])
                    lower_expected = 10 * math.log10((min_val**2) / ((max_error**2) * 2.1 / samples))
                    upper_expected = 10 * math.log10((min_val**2) / ((max_error**2) * 1.9 / samples))

                    result = compute_psnr(grain_a, grain_b)
                    self.assertEqual(len(result), channels)
                    self.assertGreater(result, [lower_expected] * channels)
                    self.assertLess(result, [upper_expected] * channels)
