#
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

from mediagrains.numpy import AudioGrain
from mediagrains.cogenums import (
    CogAudioFormat,
    COG_AUDIO_FORMAT_DEPTH,
    COG_AUDIO_FORMAT_DEPTH_S16,
    COG_AUDIO_FORMAT_DEPTH_S24,
    COG_AUDIO_FORMAT_DEPTH_S32,
    COG_AUDIO_IS_FLOAT,
    COG_AUDIO_IS_DOUBLE
)
from mediagrains import grain_constructors as bytesgrain_constructors

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

PCM_24BIT_FORMATS = [
    CogAudioFormat.S24_PLANES,
    CogAudioFormat.S24_PAIRS,
    CogAudioFormat.S24_INTERLEAVED,
]


class TestGrain (TestCase):
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

    def _create_audio_grain(self, fmt, test_data, constructor=AudioGrain, grain_data=None):
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

    def _assert_channel_data_equal(self, grain, test_data):
        """Assert that the channel data equals the test data"""
        channels = len(test_data)
        samples = len(test_data[0])
        for c in range(channels):
            for s in range(samples):
                if COG_AUDIO_FORMAT_DEPTH(grain.format) == COG_AUDIO_FORMAT_DEPTH_S24:
                    # Undo the 24-bit to 32-bit range conversion for the comparison
                    channel_sample = grain.channel_data[c][s] // 256
                else:
                    channel_sample = grain.channel_data[c][s]

                if COG_AUDIO_IS_FLOAT(grain.format) or COG_AUDIO_IS_DOUBLE(grain.format):
                    self.assertAlmostEqual(test_data[c][s], channel_sample, delta=2**(-31))
                else:
                    self.assertEqual(test_data[c][s], channel_sample)

    def test_channel_data(self):
        """Check the channel data equals the input data"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    grain = self._create_audio_grain(fmt, test_data)
                    self._assert_channel_data_equal(grain, test_data)

    def test_set_data(self):
        """Check that the Grain data can be set"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    reversed_test_data = [list(reversed(c_data)) for c_data in test_data]

                    # Create with the reversed data and then assign the original
                    grain = self._create_audio_grain(fmt, reversed_test_data)
                    grain.data = construct_audio_grain_data(fmt, test_data)

                    self._assert_channel_data_equal(grain, test_data)

    def test_create_from_bytesgrain(self):
        """Check that the numpy Grain an be created from a bytes Grain"""
        for fmt in PCM_FORMATS:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    bytes_grain = self._create_audio_grain(
                        fmt, test_data, constructor=bytesgrain_constructors.AudioGrain
                    )
                    grain = AudioGrain(bytes_grain)
                    self._assert_channel_data_equal(grain, test_data)

    def test_mod_channel_data(self):
        """Check that modified channel data is reflected in the Grain's 'data'.

        Modifications to 24-bit format sample data is not reflected in the Grain's 'data'"""
        mod_formats = [fmt for fmt in PCM_FORMATS if fmt not in PCM_24BIT_FORMATS]
        for fmt in mod_formats:
            for channels in range(1, 4):
                with self.subTest(format=fmt, channels=channels):
                    test_data = self._create_test_data(fmt, channels)
                    reversed_test_data = [list(reversed(c_data)) for c_data in test_data]

                    # Assign reversed data and then modify the channel data to the original
                    mod_grain = self._create_audio_grain(fmt, reversed_test_data)
                    for c in range(channels):
                        mod_grain.channel_data[c][:] = test_data[c][:]

                    # Create a new grain from the metadata and data
                    grain = AudioGrain(mod_grain.meta, mod_grain.data)

                    self._assert_channel_data_equal(grain, test_data)

    async def test_audio_grain_async_await(self):
        """Check that grain data can be awaited"""
        fmt = CogAudioFormat.S16_INTERLEAVED
        test_data = self._create_test_data(fmt, 2)

        async def _get_data():
            return construct_audio_grain_data(fmt, test_data)

        data_awaitable = _get_data()

        grain = self._create_audio_grain(fmt, test_data, grain_data=data_awaitable)

        self.assertIsNone(grain.data)
        self.assertEqual(len(grain.channel_data), 0)

        await grain
        self._assert_channel_data_equal(grain, test_data)

    async def test_audio_grain_async_context(self):
        """Check that the grain data can be awaited via a context"""
        fmt = CogAudioFormat.S16_INTERLEAVED
        test_data = self._create_test_data(fmt, 2)

        async def _get_data():
            return construct_audio_grain_data(fmt, test_data)

        data_awaitable = _get_data()

        grain = self._create_audio_grain(fmt, test_data, grain_data=data_awaitable)

        self.assertIsNone(grain.data)
        self.assertEqual(len(grain.channel_data), 0)

        async with grain as _grain:
            self._assert_channel_data_equal(_grain, test_data)
