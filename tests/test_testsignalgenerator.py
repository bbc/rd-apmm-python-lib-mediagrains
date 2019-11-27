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

from uuid import UUID
from mediatimestamp.immutable import Timestamp, TimeOffset
from fractions import Fraction
import struct
from math import sin, pi

from mediagrains.cogenums import CogFrameFormat, CogAudioFormat
from mediagrains.testsignalgenerator import LumaSteps, Tone1K, Silence, ColourBars, MovingBarOverlay


src_id = UUID("f2b6a9b4-2ea8-11e8-a468-878cf869cbec")
flow_id = UUID("fe3f1866-2ea8-11e8-a4bf-4b67c4a43abd")
origin_timestamp = Timestamp.from_tai_sec_nsec("417798915:0")


class TestTone1K(TestCase):
    def test_tone1k_s16_interleaved(self):
        """Testing that Tone1K generator produces correct audio grains when
        channels is 2 and sample_rate is 48000"""
        UUT = Tone1K(src_id, flow_id, channels=2, origin_timestamp=origin_timestamp, sample_rate=48000)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(25, 1))
            self.assertEqual(grain.length, 4*1920)

            data = struct.unpack('@' + ('h' * 2 * 1920), grain.data)

            for n in range(0, 1920):
                self.assertEqual(data[2*n + 0], round(sin(2.0*n*pi/48.0)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               round(sin(2.0*n*pi/48.0)*(1 << 14))))
                self.assertEqual(data[2*n + 1], round(sin(2.0*n*pi/48.0)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               round(sin(2.0*n*pi/48.0)*(1 << 14))))
            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_tone1k_s16_interleaved_at_44_1k(self):
        """Testing that Tone1K generator produces correct audio grains when
        channels is 2 and sample_rate is 44100Hz"""
        UUT = Tone1K(src_id, flow_id, channels=2, samples=1764, origin_timestamp=origin_timestamp, sample_rate=44100)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        offs = 0
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(25, 1))
            self.assertEqual(grain.length, 4*1764)

            data = struct.unpack('@' + ('h' * 2 * 1764), grain.data)

            for n in range(0, 1764):
                self.assertEqual(data[2*n + 0], round(sin(2.0*offs*pi/44.1)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               round(sin(2.0*offs*pi/44.1)*(1 << 14))))
                self.assertEqual(data[2*n + 1], round(sin(2.0*offs*pi/44.1)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               round(sin(2.0*offs*pi/44.1)*(1 << 14))))
                offs += 1
            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_tone1k_s16_interleaved_1024samples(self):
        """Testing that Tone1K generator produces correct audio grains when
        channels is 2 and samples is 1024"""
        UUT = Tone1K(src_id, flow_id, channels=2, samples=1024, origin_timestamp=origin_timestamp, sample_rate=48000)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        offs = 0
        N = 0
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(375, 8))
            self.assertEqual(grain.length, 4*1024)

            data = struct.unpack('@' + ('h' * 2 * 1024), grain.data)

            for n in range(0, 1024):
                self.assertEqual(data[2*n + 0], round(sin(2.0*offs*pi/48.0)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               round(sin(2.0*offs*pi/48.0)*(1 << 14))))
                self.assertEqual(data[2*n + 1], round(sin(2.0*offs*pi/48.0)*(1 << 14)),
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               round(sin(2.0*offs*pi/48.0)*(1 << 14))))
                offs += 1
                offs %= 48
            N += 1
            ts = origin_timestamp + TimeOffset.from_count(N, 375, 8)


class TestSilence(TestCase):
    def test_silence_s16_interleaved(self):
        """Testing that Silence generator produces correct audio grains when
        channels is 2 and sample_rate is 48000"""
        UUT = Silence(src_id, flow_id, channels=2, origin_timestamp=origin_timestamp, sample_rate=48000)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(25, 1))
            self.assertEqual(grain.length, 4*1920)

            data = struct.unpack('@' + ('h' * 2 * 1920), grain.data)

            for n in range(0, 1920):
                self.assertEqual(data[2*n + 0], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               0))
                self.assertEqual(data[2*n + 1], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               0))
            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_silence_s16_interleaved_at_44_1k(self):
        """Testing that Silence generator produces correct audio grains when
        channels is 2 and sample_rate is 44100Hz"""
        UUT = Silence(src_id, flow_id, channels=2, samples=1764, origin_timestamp=origin_timestamp, sample_rate=44100)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        offs = 0
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(25, 1))
            self.assertEqual(grain.length, 4*1764)

            data = struct.unpack('@' + ('h' * 2 * 1764), grain.data)

            for n in range(0, 1764):
                self.assertEqual(data[2*n + 0], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               0))
                self.assertEqual(data[2*n + 1], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               0))
                offs += 1
            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_silence_s16_interleaved_1024samples(self):
        """Testing that Silence generator produces correct audio grains when
        channels is 2 and samples is 1024"""
        UUT = Silence(src_id, flow_id, channels=2, samples=1024, origin_timestamp=origin_timestamp, sample_rate=48000)

        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        offs = 0
        N = 0
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogAudioFormat.S16_INTERLEAVED)
            self.assertEqual(grain.rate, Fraction(375, 8))
            self.assertEqual(grain.length, 4*1024)

            data = struct.unpack('@' + ('h' * 2 * 1024), grain.data)

            for n in range(0, 1024):
                self.assertEqual(data[2*n + 0], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n,
                                                                                                               data[2*n + 0],
                                                                                                               0))
                self.assertEqual(data[2*n + 1], 0,
                                 msg="Sample {} has value {} which does not match expected value of {}".format(2*n + 1,
                                                                                                               data[2*n + 1],
                                                                                                               0))
                offs += 1
                offs %= 48
            N += 1
            ts = origin_timestamp + TimeOffset.from_count(N, 375, 8)


class TestLumaSteps(TestCase):
    def test_lumasteps_u8_444(self):
        """Testing that the LumaSteps generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4
        UUT = LumaSteps(src_id, flow_id, width, height,
                        origin_timestamp=origin_timestamp)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.U8_444)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            luma = [16 + (i*(235-16)//8) for i in range(0, 8)]

            for y in range(0, height):
                for x in range(0, width):
                    self.assertEqual(Y[y*grain.components[0].stride + x], luma[x//(width//8)])
                    self.assertEqual(U[y*grain.components[1].stride + x], 128)
                    self.assertEqual(V[y*grain.components[2].stride + x], 128)

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_lumasteps_s16_422_10bit(self):
        """Testing that the LumaSteps generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4
        UUT = LumaSteps(src_id, flow_id, width, height,
                        origin_timestamp=origin_timestamp,
                        cog_frame_format=CogFrameFormat.S16_422_10BIT)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            luma = [64 + (i*(940-64)//8) for i in range(0, 8)]

            for y in range(0, height):
                for x in range(0, width):
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 0], luma[x//(width//8)] & 0xFF)
                    self.assertEqual(Y[y*grain.components[0].stride + 2*x + 1], (luma[x//(width//8)] >> 8) & 0xFF)
                for x in range(0, width//2):
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], 0)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], 2)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], 0)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], 2)

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_lumasteps_raises_on_invalid_format(self):
        width = 240
        height = 4

        UUT = LumaSteps(src_id, flow_id, width, height,
                        origin_timestamp=origin_timestamp,
                        cog_frame_format=CogFrameFormat.UNKNOWN)

        with self.assertRaises(ValueError):
            next(UUT)

    def test_lumasteps_with_step_2(self):
        """Testing that the LumaSteps generator produces alternate frames when skip is set"""
        width = 240
        height = 4
        rate = Fraction(50, 1)
        step = 2
        UUT = LumaSteps(src_id, flow_id, width, height,
                        origin_timestamp=origin_timestamp,
                        cog_frame_format=CogFrameFormat.S16_422_10BIT,
                        rate=rate,
                        step=step)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            ts = Timestamp.from_count(ts.to_count(rate.numerator, rate.denominator) + step,
                                      rate.numerator, rate.denominator)


class TestColourBars(TestCase):
    colourbars_expected_values_8bit = [
        (0xFF, 0x80, 0x80),
        (0xE1, 0x00, 0x94),
        (0xB2, 0xAB, 0x00),
        (0x95, 0x2B, 0x15),
        (0x69, 0xD4, 0xEA),
        (0x4C, 0x54, 0xFF),
        (0x1D, 0xFF, 0x6B),
        (0x00, 0x80, 0x80)]

    colourbars_expected_values_10bit = [
        (0x3FF, 0x200, 0x200),
        (0x387, 0x000, 0x250),
        (0x2C8, 0x2AF, 0x000),
        (0x257, 0x0AF, 0x057),
        (0x1A7, 0x350, 0x3A8),
        (0x130, 0x150, 0x3FF),
        (0x077, 0x3FF, 0x1AF),
        (0x000, 0x200, 0x200)]

    def test_colourbars100_u8_444(self):
        """Testing that the ColourBars generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4
        UUT = ColourBars(src_id, flow_id,
                         width, height,
                         intensity=1.0,
                         origin_timestamp=origin_timestamp,
                         cog_frame_format=CogFrameFormat.U8_444,
                         rate=Fraction(25, 1),
                         step=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.U8_444)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = self.colourbars_expected_values_8bit

            for y in range(0, height):
                for x in range(0, width):
                    self.assertEqual(Y[y*grain.components[0].stride + x], expected[x//(width//8)][0])
                    self.assertEqual(U[y*grain.components[1].stride + x], expected[x//(width//8)][1])
                    self.assertEqual(V[y*grain.components[2].stride + x], expected[x//(width//8)][2])

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_colourbars75_u8_444(self):
        """Testing that the ColourBars generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4
        UUT = ColourBars(src_id, flow_id,
                         width, height,
                         intensity=0.75,
                         origin_timestamp=origin_timestamp,
                         cog_frame_format=CogFrameFormat.U8_444,
                         rate=Fraction(25, 1),
                         step=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.U8_444)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = self.colourbars_expected_values_8bit

            for y in range(0, height):
                for x in range(0, width):
                    self.assertEqual(Y[y*grain.components[0].stride + x], int(0.75*expected[x//(width//8)][0]))
                    self.assertEqual(U[y*grain.components[1].stride + x], expected[x//(width//8)][1])
                    self.assertEqual(V[y*grain.components[2].stride + x], expected[x//(width//8)][2])

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_colourbars75_s16_422_10bit(self):
        """Testing that the ColourBars generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken
        for testing under control"""
        width = 240
        height = 4
        UUT = ColourBars(src_id, flow_id,
                         width, height,
                         intensity=0.75,
                         origin_timestamp=origin_timestamp,
                         cog_frame_format=CogFrameFormat.S16_422_10BIT,
                         rate=Fraction(25, 1),
                         step=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = self.colourbars_expected_values_10bit

            for y in range(0, height):
                for x in range(0, width//2):
                    self.assertEqual(Y[y*grain.components[0].stride + 4*x + 0], int(0.75*expected[(2*x + 0)//(width//8)][0]) & 0xFF)
                    self.assertEqual(Y[y*grain.components[0].stride + 4*x + 1], int(0.75*expected[(2*x + 0)//(width//8)][0]) >> 8)
                    self.assertEqual(Y[y*grain.components[0].stride + 4*x + 2], int(0.75*expected[(2*x + 1)//(width//8)][0]) & 0xFF)
                    self.assertEqual(Y[y*grain.components[0].stride + 4*x + 3], int(0.75*expected[(2*x + 1)//(width//8)][0]) >> 8)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], expected[x//(width//16)][1] & 0xFF)
                    self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], expected[x//(width//16)][1] >> 8)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], expected[x//(width//16)][2] & 0xFF)
                    self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], expected[x//(width//16)][2] >> 8)

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)


class TestMovingBarOverlay(TestCase):
    def test_movingbar_colourbars100_u8_444(self):
        """Testing that the ColourBars with MovingBarOverlay generators produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken for testing under control"""
        width = 240
        height = 4
        UUT = MovingBarOverlay(ColourBars(src_id, flow_id,
                                          width, height,
                                          intensity=1.0,
                                          origin_timestamp=origin_timestamp,
                                          cog_frame_format=CogFrameFormat.U8_444,
                                          rate=Fraction(25, 1),
                                          step=1),
                               height=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.U8_444)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = TestColourBars.colourbars_expected_values_8bit

            fnum = grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator)
            for y in range(0, height):
                if (fnum % height) == y:
                    for x in range(0, width):
                        self.assertEqual(Y[y*grain.components[0].stride + x], 16)
                        self.assertEqual(U[y*grain.components[1].stride + x], 128)
                        self.assertEqual(V[y*grain.components[2].stride + x], 128)
                else:
                    for x in range(0, width):
                        self.assertEqual(Y[y*grain.components[0].stride + x], expected[x//(width//8)][0])
                        self.assertEqual(U[y*grain.components[1].stride + x], expected[x//(width//8)][1])
                        self.assertEqual(V[y*grain.components[2].stride + x], expected[x//(width//8)][2])

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_movingbar_colourbars75_u8_444(self):
        """Testing that the ColourBars with MovingBarOverlay generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken for testing under control"""
        width = 240
        height = 4
        UUT = MovingBarOverlay(ColourBars(src_id, flow_id,
                                          width, height,
                                          intensity=0.75,
                                          origin_timestamp=origin_timestamp,
                                          cog_frame_format=CogFrameFormat.U8_444,
                                          rate=Fraction(25, 1),
                                          step=1),
                               height=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.U8_444)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = TestColourBars.colourbars_expected_values_8bit

            fnum = grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator)

            for y in range(0, height):
                if (fnum % height) == y:
                    for x in range(0, width):
                        self.assertEqual(Y[y*grain.components[0].stride + x], 16)
                        self.assertEqual(U[y*grain.components[1].stride + x], 128)
                        self.assertEqual(V[y*grain.components[2].stride + x], 128)
                else:
                    for x in range(0, width):
                        self.assertEqual(Y[y*grain.components[0].stride + x], int(0.75*expected[x//(width//8)][0]))
                        self.assertEqual(U[y*grain.components[1].stride + x], expected[x//(width//8)][1])
                        self.assertEqual(V[y*grain.components[2].stride + x], expected[x//(width//8)][2])

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)

    def test_movingbar_colourbars75_s16_422_10bit(self):
        """Testing that the ColourBars with MovingBarOverlay generator produces correct video frames
        when the height is 4 lines and the width 240 pixels (to keep time taken for testing under control"""
        width = 240
        height = 4
        UUT = MovingBarOverlay(ColourBars(src_id, flow_id,
                                          width, height,
                                          intensity=0.75,
                                          origin_timestamp=origin_timestamp,
                                          cog_frame_format=CogFrameFormat.S16_422_10BIT,
                                          rate=Fraction(25, 1),
                                          step=1),
                               height=1)

        # Extracts the first 10 grains from the generator
        grains = [grain for _, grain in zip(range(10), UUT)]

        ts = origin_timestamp
        for grain in grains:
            self.assertEqual(grain.source_id, src_id)
            self.assertEqual(grain.flow_id, flow_id)
            self.assertEqual(grain.origin_timestamp, ts)
            self.assertEqual(grain.sync_timestamp, ts)
            self.assertEqual(grain.format, CogFrameFormat.S16_422_10BIT)
            self.assertEqual(grain.rate, Fraction(25, 1))

            Y = grain.data[grain.components[0].offset:grain.components[0].offset + grain.components[0].length]
            U = grain.data[grain.components[1].offset:grain.components[1].offset + grain.components[1].length]
            V = grain.data[grain.components[2].offset:grain.components[2].offset + grain.components[2].length]

            expected = TestColourBars.colourbars_expected_values_10bit

            fnum = grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator)

            for y in range(0, height):
                if (fnum % height) == y:
                    for x in range(0, width//2):
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 0], 64)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 1], 0)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 2], 64)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 3], 0)
                        self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], 0)
                        self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], 2)
                        self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], 0)
                        self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], 2)
                else:
                    for x in range(0, width//2):
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 0], int(0.75*expected[(2*x + 0)//(width//8)][0]) & 0xFF)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 1], int(0.75*expected[(2*x + 0)//(width//8)][0]) >> 8)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 2], int(0.75*expected[(2*x + 1)//(width//8)][0]) & 0xFF)
                        self.assertEqual(Y[y*grain.components[0].stride + 4*x + 3], int(0.75*expected[(2*x + 1)//(width//8)][0]) >> 8)
                        self.assertEqual(U[y*grain.components[1].stride + 2*x + 0], expected[x//(width//16)][1] & 0xFF)
                        self.assertEqual(U[y*grain.components[1].stride + 2*x + 1], expected[x//(width//16)][1] >> 8)
                        self.assertEqual(V[y*grain.components[2].stride + 2*x + 0], expected[x//(width//16)][2] & 0xFF)
                        self.assertEqual(V[y*grain.components[2].stride + 2*x + 1], expected[x//(width//16)][2] >> 8)

            ts = Timestamp.from_count(ts.to_count(25, 1) + 1, 25, 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
