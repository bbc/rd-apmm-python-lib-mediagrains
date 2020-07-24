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

from uuid import UUID
from mediatimestamp.immutable import Timestamp
from mediatimestamp import TimeValueRange
from fractions import Fraction
import random
import struct
from math import pi, sin

from mediagrains.cogenums import (
    CogFrameFormat,
    CogAudioFormat,
    COG_FRAME_FORMAT_ACTIVE_BITS,
    COG_FRAME_FORMAT_BYTES_PER_VALUE,
    COG_FRAME_FORMAT_H_SHIFT,
    COG_FRAME_FORMAT_V_SHIFT)
from mediagrains.patterngenerators.video import LumaSteps, ColourBars, MovingBarOverlay
from mediagrains.patterngenerators.audio import Tone1K, Tone, Silence


src_id = UUID("f2b6a9b4-2ea8-11e8-a468-878cf869cbec")
flow_id = UUID("fe3f1866-2ea8-11e8-a4bf-4b67c4a43abd")
origin_timestamp = Timestamp.from_tai_sec_nsec("417798915:0")

random.seed(0)


class PatternGeneratorTestCase(TestCase):
    """General superclass for test cases intended to test PatternGenerator subclasses
    """

    def assertTestSignalGeneratorGrainsPassAssertion(self, factory, assertion, name=None):
        """Asserts that the provided factory (Callable[[], PatternGenerator]) returns
        a generator which can be accessed with slices, ranges, and individual timevalues
        in both sequential and random access, and also supports stepping when accessed with a
        slice. All the returned grains will be checked with the supplied assertion method
        (Callable[[GRAIN, Timestamp], None]).

        If a name is provided it will be used for labelling subTests.
        """
        # We use three different sets of 10 timestamps, one sequential, one ordered and skipping every other value, the last random
        ordered_timestamps = [Timestamp.from_count(origin_timestamp.to_count(25, 1) + n, 25, 1) for n in range(0, 10)]
        even_timestamps = [Timestamp.from_count(origin_timestamp.to_count(25, 1) + 2*n, 25, 1) for n in range(0, 10)]
        unordered_timestamps = [Timestamp.from_count(origin_timestamp.to_count(25, 1) + n, 25, 1) for n in (random.randrange(0, 100) for n in range(0, 10))]

        # The various different modes of indexing we can test
        indexing_modes = [
            {
                'name': 'slice',
                'factory': (lambda UUT: UUT[origin_timestamp:]),
                'timestamps': ordered_timestamps
            },
            {
                'name': 'slice, skipping alternate frames',
                'factory': (lambda UUT: UUT[origin_timestamp::2]),
                'timestamps': even_timestamps
            },
            {
                'name': 'TimeValueRange',
                'factory': (lambda UUT: UUT[TimeValueRange.from_start(origin_timestamp)]),
                'timestamps': ordered_timestamps
            },
            {
                'name': 'Sequential TimeValues',
                'factory': (lambda UUT: (UUT[ts] for ts in ordered_timestamps)),
                'timestamps': ordered_timestamps
            },
            {
                'name': 'Random access TimeValues',
                'factory': (lambda UUT: (UUT[ts] for ts in unordered_timestamps)),
                'timestamps': unordered_timestamps
            }
        ]

        if name is None:
            name = "assertTestSignalGeneratorGrainsPassAssertion"

        # Extracts the first 10 grains from the generator and verifies them
        for im in indexing_modes:
            with self.subTest(name=f"{name}, indexed by {im['name']}"):
                UUT = factory()
                for ts, grain in zip(im['timestamps'], im['factory'](UUT)):
                    with self.subTest(ts=ts):
                        assertion(grain, ts)


class VideoPatternGeneratorTestCase(PatternGeneratorTestCase):
    def assertIsVideoGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        width=240,
        height=4,
        cog_frame_format=CogFrameFormat.U8_444,
        rate=Fraction(25, 1)
    ):
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ts)
        self.assertEqual(grain.sync_timestamp, ts)
        self.assertEqual(grain.format, cog_frame_format)
        self.assertEqual(grain.rate, rate)


class TestLumaSteps(VideoPatternGeneratorTestCase):
    def assertIsLumaStepsGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        width=240,
        height=4,
        cog_frame_format=CogFrameFormat.U8_444,
        rate=Fraction(25, 1)
    ):
        self.assertIsVideoGrain(
            grain,
            ts,
            src_id=src_id,
            flow_id=flow_id,
            width=width,
            height=height,
            cog_frame_format=cog_frame_format,
            rate=rate)

        Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
        U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
        V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

        bytes_per_value = COG_FRAME_FORMAT_BYTES_PER_VALUE(cog_frame_format)
        active_bits = COG_FRAME_FORMAT_ACTIVE_BITS(cog_frame_format)
        h_shift = COG_FRAME_FORMAT_H_SHIFT(cog_frame_format)
        v_shift = COG_FRAME_FORMAT_V_SHIFT(cog_frame_format)
        if active_bits == 8:
            luma = [16 + (i*(235-16)//8) for i in range(0, 8)]
        elif active_bits == 10:
            luma = [64 + (i*(940-64)//8) for i in range(0, 8)]

        for y in range(0, height):
            for x in range(0, width):
                if bytes_per_value == 1:
                    self.assertEqual(Y[y*grain.components[0].stride + x], luma[x//(width//8)])
                else:
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 0], luma[x//(width//8)] & 0xFF)
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 1], (luma[x//(width//8)] >> 8) & 0xFF)
        for y in range(0, height >> v_shift):
            for x in range(0, width >> h_shift):
                if bytes_per_value == 1:
                    self.assertEqual(U[y*grain.components[1].stride + x], 1 << (active_bits - 1))
                    self.assertEqual(V[y*grain.components[2].stride + x], 1 << (active_bits - 1))
                else:
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], 0)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], (1 << (active_bits - 9)))
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], 0)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], (1 << (active_bits - 9)))

    def test_grains_for_valid_formats(self):
        """Testing that the generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4

        # The various different generator units we can test:
        UUTs = [
            {
                'name': 'Lumasteps with no cog_frame_format set',
                'factory': (lambda: LumaSteps(src_id, flow_id, width, height)),
                'expected_format': CogFrameFormat.U8_444
            },
            {
                'name': 'Lumasteps in S16_422_10BIT format',
                'factory': (lambda: LumaSteps(src_id, flow_id, width, height, cog_frame_format=CogFrameFormat.S16_422_10BIT)),
                'expected_format': CogFrameFormat.S16_422_10BIT
            }
        ]

        for UUT in UUTs:
            self.assertTestSignalGeneratorGrainsPassAssertion(
                UUT['factory'],
                lambda grain, ts: self.assertIsLumaStepsGrain(grain, ts, cog_frame_format=UUT['expected_format']),
                name=UUT['name']
            )

    def test_raises_on_invalid_format(self):
        width = 240
        height = 4

        with self.assertRaises(ValueError):
            LumaSteps(src_id, flow_id, width, height,
                      cog_frame_format=CogFrameFormat.UNKNOWN)


class TestColourBars(VideoPatternGeneratorTestCase):
    def assertIsColourBarsGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        width=240,
        height=4,
        cog_frame_format=CogFrameFormat.U8_444,
        rate=Fraction(25, 1),
        intensity=0.75
    ):
        self.assertIsVideoGrain(
            grain,
            ts,
            src_id=src_id,
            flow_id=flow_id,
            width=width,
            height=height,
            cog_frame_format=cog_frame_format,
            rate=rate)

        Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
        U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
        V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

        bytes_per_value = COG_FRAME_FORMAT_BYTES_PER_VALUE(cog_frame_format)
        active_bits = COG_FRAME_FORMAT_ACTIVE_BITS(cog_frame_format)
        h_shift = COG_FRAME_FORMAT_H_SHIFT(cog_frame_format)
        v_shift = COG_FRAME_FORMAT_V_SHIFT(cog_frame_format)

        _steps = 8
        bs = 16 - active_bits

        values = [
            (int((0xFFFF >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs),
            (int((0xE1FF >> bs) * intensity), 0x0000 >> bs, 0x9400 >> bs),
            (int((0xB200 >> bs) * intensity), 0xABFF >> bs, 0x0000 >> bs),
            (int((0x95FF >> bs) * intensity), 0x2BFF >> bs, 0x15FF >> bs),
            (int((0x69FF >> bs) * intensity), 0xD400 >> bs, 0xEA00 >> bs),
            (int((0x4C00 >> bs) * intensity), 0x5400 >> bs, 0xFFFF >> bs),
            (int((0x1DFF >> bs) * intensity), 0xFFFF >> bs, 0x6BFF >> bs),
            (int((0x0000 >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs)]

        for y in range(0, height):
            for x in range(0, width):
                pos = x // (width // _steps)
                val = values[pos]
                if bytes_per_value == 1:
                    self.assertEqual(Y[y*grain.components[0].stride + x], val[0])
                else:
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 0], val[0] & 0xFF)
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 1], (val[0] >> 8) & 0xFF)
        for y in range(0, height >> v_shift):
            for x in range(0, width >> h_shift):
                pos = x // ((width >> h_shift) // _steps)
                val = values[pos]
                if bytes_per_value == 1:
                    self.assertEqual(U[y*grain.components[1].stride + x], val[1])
                    self.assertEqual(V[y*grain.components[2].stride + x], val[2])
                else:
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], val[1] & 0xFF)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], (val[1] >> 8) & 0xFF)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], val[2] & 0xFF)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], (val[2] >> 8) & 0xFF)

    def test_grains_for_valid_formats(self):
        """Testing that the generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4

        # The various different generator units we can test:
        UUTs = [
            {
                'name': '.75 Colourbars with no cog_frame_format set',
                'factory': (lambda: ColourBars(src_id, flow_id, width, height)),
                'expected_format': CogFrameFormat.U8_444,
                'intensity': 0.75
            },
            {
                'name': '.75 Colourbars in S16_422_10BIT format',
                'factory': (lambda: ColourBars(src_id, flow_id, width, height, cog_frame_format=CogFrameFormat.S16_422_10BIT)),
                'expected_format': CogFrameFormat.S16_422_10BIT,
                'intensity': 0.75
            },
            {
                'name': '100% Colourbars with no cog_frame_format set',
                'factory': (lambda: ColourBars(src_id, flow_id, width, height, intensity=1.0)),
                'expected_format': CogFrameFormat.U8_444,
                'intensity': 1.0
            },
            {
                'name': '100% Colourbars in S16_422_10BIT format',
                'factory': (lambda: ColourBars(src_id, flow_id, width, height, cog_frame_format=CogFrameFormat.S16_422_10BIT, intensity=1.0)),
                'expected_format': CogFrameFormat.S16_422_10BIT,
                'intensity': 1.0
            }
        ]

        for UUT in UUTs:
            self.assertTestSignalGeneratorGrainsPassAssertion(
                UUT['factory'],
                lambda grain, ts: self.assertIsColourBarsGrain(grain, ts, cog_frame_format=UUT['expected_format'], intensity=UUT['intensity']),
                name=UUT['name']
            )

    def test_raises_on_invalid_format(self):
        width = 240
        height = 4

        with self.assertRaises(ValueError):
            ColourBars(src_id, flow_id, width, height,
                       cog_frame_format=CogFrameFormat.UNKNOWN)


class TestMovingBarOverlay(VideoPatternGeneratorTestCase):
    def assertIsColourBarsWithMovingBarGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        width=240,
        height=4,
        cog_frame_format=CogFrameFormat.U8_444,
        rate=Fraction(25, 1),
        intensity=0.75,
        bar_height=1,
        bar_speed=1
    ):
        self.assertIsVideoGrain(
            grain,
            ts,
            src_id=src_id,
            flow_id=flow_id,
            width=width,
            height=height,
            cog_frame_format=cog_frame_format,
            rate=rate)

        Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
        U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
        V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

        bytes_per_value = COG_FRAME_FORMAT_BYTES_PER_VALUE(cog_frame_format)
        active_bits = COG_FRAME_FORMAT_ACTIVE_BITS(cog_frame_format)
        h_shift = COG_FRAME_FORMAT_H_SHIFT(cog_frame_format)
        v_shift = COG_FRAME_FORMAT_V_SHIFT(cog_frame_format)

        _steps = 8
        bs = 16 - active_bits

        values = [
            (int((0xFFFF >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs),
            (int((0xE1FF >> bs) * intensity), 0x0000 >> bs, 0x9400 >> bs),
            (int((0xB200 >> bs) * intensity), 0xABFF >> bs, 0x0000 >> bs),
            (int((0x95FF >> bs) * intensity), 0x2BFF >> bs, 0x15FF >> bs),
            (int((0x69FF >> bs) * intensity), 0xD400 >> bs, 0xEA00 >> bs),
            (int((0x4C00 >> bs) * intensity), 0x5400 >> bs, 0xFFFF >> bs),
            (int((0x1DFF >> bs) * intensity), 0xFFFF >> bs, 0x6BFF >> bs),
            (int((0x0000 >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs)]

        if active_bits == 8:
            black = [16, 128, 128]
        else:
            black = [64, 512, 512]

        fnum = grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator)

        bar_start = ((fnum * bar_speed) % height)
        bar_end = ((fnum * bar_speed + bar_height) % height)

        for y in range(0, height):
            with self.subTest(bar_start=bar_start, bar_end=bar_end, y=y):
                for x in range(0, width):
                    if (bar_start <= y < bar_end) or (bar_end < bar_start <= y) or (y < bar_end < bar_start):
                        val = black
                    else:
                        pos = x // (width // _steps)
                        val = values[pos]
                    if bytes_per_value == 1:
                        self.assertEqual(Y[y*grain.components[0].stride + x], val[0])
                    else:
                        self.assertEqual(Y[y*grain.components[0].stride + 2*x + 0], val[0] & 0xFF)
                        self.assertEqual(Y[y*grain.components[0].stride + 2*x + 1], (val[0] >> 8) & 0xFF)
        for y in range(0, height >> v_shift):
            for x in range(0, width >> h_shift):
                if (bar_start <= y < bar_end) or (bar_end < bar_start <= y) or (y < bar_end < bar_start):
                    val = black
                else:
                    pos = x // ((width >> h_shift) // _steps)
                    val = values[pos]
                if bytes_per_value == 1:
                    self.assertEqual(U[y*grain.components[1].stride + x], val[1])
                    self.assertEqual(V[y*grain.components[2].stride + x], val[2])
                else:
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], val[1] & 0xFF)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], (val[1] >> 8) & 0xFF)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], val[2] & 0xFF)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], (val[2] >> 8) & 0xFF)

    def test_grains_for_valid_formats(self):
        """Testing that the generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4

        # The various different generator units we can test:
        UUTs = []

        def MovingBarTestFactory(cog_frame_format, intensity, bar_height):
            def __inner():
                return MovingBarOverlay(ColourBars(src_id, flow_id, width, height, intensity=intensity, cog_frame_format=cog_frame_format), height=bar_height)
            return __inner

        for bar_height in [1, 2]:
            for intensity in [0.75, 1.0]:
                for (fmt_name, fmt) in [('U8_444', CogFrameFormat.U8_444), ('S16_422_10BIT', CogFrameFormat.S16_422_10BIT)]:
                    UUTs.append(
                        {
                            'name': f'{intensity} Colourbars in {fmt_name} format w/ {bar_height}px black bar',
                            'factory': MovingBarTestFactory(fmt, intensity, bar_height),
                            'expected_format': fmt,
                            'intensity': intensity,
                            'bar_height': bar_height
                        }
                    )

        for UUT in UUTs:
            self.assertTestSignalGeneratorGrainsPassAssertion(
                UUT['factory'],
                lambda grain, ts: self.assertIsColourBarsWithMovingBarGrain(
                    grain, ts, cog_frame_format=UUT['expected_format'], intensity=UUT['intensity'], bar_height=UUT['bar_height']),
                name=UUT['name']
            )

    def test_raises_on_invalid_format(self):
        width = 240
        height = 4

        with self.assertRaises(ValueError):
            MovingBarOverlay(
                ColourBars(
                    src_id,
                    flow_id,
                    width,
                    height,
                    cog_frame_format=CogFrameFormat.UNKNOWN),
                height=1)


class AudioPatternGeneratorTestCase(PatternGeneratorTestCase):
    def assertIsAudioGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
        grain_rate=Fraction(25, 1),
        sample_rate=48000,
        channels=2,
        samples=None
    ):
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ts)
        self.assertEqual(grain.sync_timestamp, ts)
        self.assertEqual(grain.format, cog_audio_format)
        self.assertEqual(grain.rate, grain_rate)
        self.assertEqual(grain.sample_rate, sample_rate)
        self.assertEqual(grain.channels, channels)
        if samples is None:
            samples = sample_rate // grain_rate
        self.assertEqual(grain.samples, samples)

    def assertIsAudioGrainWithRepeatingSamples(
        self,
        grain,
        ts,
        expected_samples,
        src_id=src_id,
        flow_id=flow_id,
        cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
        grain_rate=Fraction(25, 1),
        sample_rate=48000,
        channels=2,
        samples=None,
    ):
        if samples is None:
            samples = sample_rate // grain_rate

        self.assertIsAudioGrain(
            grain,
            ts,
            src_id=src_id,
            flow_id=flow_id,
            cog_audio_format=cog_audio_format,
            grain_rate=grain_rate,
            sample_rate=sample_rate,
            channels=channels,
            samples=samples)

        if cog_audio_format == CogAudioFormat.S16_INTERLEAVED:
            data = struct.unpack('@' + ('h' * channels * samples), grain.data)

            for n in range(0, samples):
                expected = expected_samples(n)
                self.assertEqual(data[2*n + 0], expected,
                                 msg=f"Sample {2*n} has value {data[2*n + 0]} which does not match expected value of {expected}")
                self.assertEqual(data[2*n + 1], expected,
                                 msg=f"Sample {2*n} has value {data[2*n + 0]} which does not match expected value of {expected}")
        else:
            self.fail(f"Unsupported audio grain format: {cog_audio_format!r}")


class TestTone(AudioPatternGeneratorTestCase):
    def assertIsToneGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
        grain_rate=Fraction(25, 1),
        sample_rate=48000,
        channels=2,
        frequency=1000,
        samples=None
    ):
        if samples is None:
            samples = sample_rate // grain_rate

        self.assertIsAudioGrainWithRepeatingSamples(
            grain,
            ts,
            expected_samples=lambda n: round(sin(2.0*frequency*n*pi/sample_rate)*(1 << 14)),
            src_id=src_id,
            flow_id=flow_id,
            cog_audio_format=cog_audio_format,
            grain_rate=grain_rate,
            sample_rate=sample_rate,
            channels=channels,
            samples=samples)

    def test_grains_for_valid_formats(self):
        """Testing that the generator produces correct audio frames"""

        # The various different generator units we can test:
        UUTs = [
            {
                'name': 'Tone1K with no cog_audio_format set, at 48K sampling with 2 channels',
                'factory': (lambda: Tone1K(src_id, flow_id, channels=2, sample_rate=48000)),
                'channels': 2,
                'sample_rate': 48000,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 1000
            },
            {
                'name': 'Tone1K with no cog_audio_format set, at 44.1K sampling with 2 channels',
                'factory': (lambda: Tone1K(src_id, flow_id, channels=2, sample_rate=44100, samples=1764)),
                'channels': 2,
                'sample_rate': 44100,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 1000
            },
            {
                'name': 'Tone with no cog_audio_format set, at 48K sampling with 2 channels and frequency 1000',
                'factory': (lambda: Tone(src_id, flow_id, channels=2, sample_rate=48000, frequency=1000)),
                'channels': 2,
                'sample_rate': 48000,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 1000
            },
            {
                'name': 'Tone with no cog_audio_format set, at 44.1K sampling with 2 channels and frequency 1000',
                'factory': (lambda: Tone(src_id, flow_id, channels=2, sample_rate=44100, samples=1764, frequency=1000)),
                'channels': 2,
                'sample_rate': 44100,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 1000
            },
            {
                'name': 'Tone with no cog_audio_format set, at 48K sampling with 2 channels and frequency 2000',
                'factory': (lambda: Tone(src_id, flow_id, channels=2, sample_rate=48000, frequency=2000)),
                'channels': 2,
                'sample_rate': 48000,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 2000
            },
            {
                'name': 'Tone with no cog_audio_format set, at 44.1K sampling with 2 channels and frequency 2000',
                'factory': (lambda: Tone(src_id, flow_id, channels=2, sample_rate=44100, samples=1764, frequency=2000)),
                'channels': 2,
                'sample_rate': 44100,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
                'frequency': 2000
            }
        ]

        for UUT in UUTs:
            self.assertTestSignalGeneratorGrainsPassAssertion(
                UUT['factory'],
                lambda grain, ts: self.assertIsToneGrain(
                    grain,
                    ts,
                    cog_audio_format=UUT['expected_format'],
                    channels=UUT['channels'],
                    sample_rate=UUT['sample_rate'],
                    frequency=UUT['frequency']),
                name=UUT['name']
            )

    def test_raises_on_invalid_format(self):
        with self.assertRaises(ValueError):
            Tone1K(src_id, flow_id,
                   cog_audio_format=CogAudioFormat.UNKNOWN)

        with self.assertRaises(ValueError):
            Tone(src_id, flow_id,
                 cog_audio_format=CogAudioFormat.UNKNOWN)


class TestSilence(AudioPatternGeneratorTestCase):
    def assertIsSilentGrain(
        self,
        grain,
        ts,
        src_id=src_id,
        flow_id=flow_id,
        cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
        grain_rate=Fraction(25, 1),
        sample_rate=48000,
        channels=2,
        samples=None
    ):
        if samples is None:
            samples = sample_rate // grain_rate

        self.assertIsAudioGrainWithRepeatingSamples(
            grain,
            ts,
            expected_samples=lambda n: 0.0,
            src_id=src_id,
            flow_id=flow_id,
            cog_audio_format=cog_audio_format,
            grain_rate=grain_rate,
            sample_rate=sample_rate,
            channels=channels,
            samples=samples)

    def test_grains_for_valid_formats(self):
        """Testing that the generator produces correct audio frames"""

        # The various different generator units we can test:
        UUTs = [
            {
                'name': 'Silence with no cog_audio_format set, at 48K sampling with 2 channels',
                'factory': (lambda: Silence(src_id, flow_id, channels=2, sample_rate=48000)),
                'channels': 2,
                'sample_rate': 48000,
                'expected_format': CogAudioFormat.S16_INTERLEAVED
            },
            {
                'name': 'Silence with no cog_audio_format set, at 44.1K sampling with 2 channels',
                'factory': (lambda: Silence(src_id, flow_id, channels=2, sample_rate=44100, samples=1764)),
                'channels': 2,
                'sample_rate': 44100,
                'expected_format': CogAudioFormat.S16_INTERLEAVED,
            }
        ]

        for UUT in UUTs:
            self.assertTestSignalGeneratorGrainsPassAssertion(
                UUT['factory'],
                lambda grain, ts: self.assertIsSilentGrain(
                    grain,
                    ts,
                    cog_audio_format=UUT['expected_format'],
                    channels=UUT['channels'],
                    sample_rate=UUT['sample_rate']),
                name=UUT['name']
            )

    def test_raises_on_invalid_format(self):
        with self.assertRaises(ValueError):
            Silence(src_id, flow_id,
                    cog_audio_format=CogAudioFormat.UNKNOWN)
