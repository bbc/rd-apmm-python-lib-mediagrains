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
"""\
The submodule of mediagrains which contains code for generating test video
grains.

This module is deprecated, please use mediagrains.patterngenerators instead.
"""

from fractions import Fraction
from mediatimestamp.immutable import TimeOffset, Timestamp
from copy import deepcopy
import struct
import fractions

from deprecated import deprecated

from . import AudioGrain
from .cogenums import CogFrameFormat, CogAudioFormat
from .patterngenerators.video import LumaSteps as LumaStepsPatternGenerator
from .patterngenerators.video import ColourBars as ColourBarsPatternGenerator
from .patterngenerators.audio import Tone as TonePatternGenerator
from .patterngenerators.audio import Silence as SilencePatternGenerator

__all__ = ["LumaSteps", "Tone1K", "Tone", "Silence", "ColourBars", "MovingBarOverlay"]

# information about formats
# in the order:
# (num_bytes_per_sample, (offset, range), (offset, range), (offset, range), active_bits_per_sample)
# in YUV order
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


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def LumaSteps(src_id, flow_id, width, height,
              rate=Fraction(25, 1),
              origin_timestamp=None,
              cog_frame_format=CogFrameFormat.U8_444,
              step=1):
    """Returns a generator for video grains in U8_444 format.
    :param src_id: source_id for grains
    :param flow_id: flow_id for grains
    :param width: width of grains
    :param height: height of grains
    :param rate: rate of grains
    :param origin_timestamp: the origin timestamp of the first grain.
    :param step: The number of grains to increment by each time (values above 1 cause skipping)"""

    origin_timestamp = origin_timestamp if origin_timestamp is not None else Timestamp.get_time()
    yield from LumaStepsPatternGenerator(
        src_id,
        flow_id,
        width,
        height,
        rate=rate,
        cog_frame_format=cog_frame_format)[origin_timestamp::step]


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def ColourBars(src_id, flow_id, width, height,
               intensity=0.75,
               rate=Fraction(25, 1),
               origin_timestamp=None,
               cog_frame_format=CogFrameFormat.U8_444,
               step=1):
    """Returns a generator for colour bar video grains in specified format.
    :param src_id: source_id for grains
    :param flow_id: flow_id for grains
    :param width: width of grains
    :param height: height of grains
    :param intensity: intensity of colour bars (usually 1.0 or 0.75)
    :param rate: rate of grains
    :param origin_timestamp: the origin timestamp of the first grain.
    :param step: The number of grains to increment by each time (values above 1 cause skipping)"""

    origin_timestamp = origin_timestamp if origin_timestamp is not None else Timestamp.get_time()
    yield from ColourBarsPatternGenerator(
        src_id,
        flow_id,
        width,
        height,
        intensity=intensity,
        rate=rate,
        cog_frame_format=cog_frame_format
    )[origin_timestamp::step]


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def MovingBarOverlay(grain_gen, height=100, speed=1.0):
    """Call this method and pass an iterable of video grains as the first parameter. This method will overlay a moving black bar onto the grains.

    :param grain_gen: An iterable which yields video grains
    :param heigh: The height of the bar in pixels
    :param speed: A floating point speed in pixels per frame

    :returns: A generator which yields video grains
    """
    bar = None
    for grain in grain_gen:
        v_subs = (grain.components[0].height + grain.components[1].height - 1)//grain.components[1].height

        if bar is None:
            if grain.format not in pixel_ranges:
                raise ValueError("Not a supported format for this generator")

            _bpp = pixel_ranges[grain.format][0]

            bar = [bytearray(grain.components[0].width*_bpp * height),
                   bytearray(grain.components[1].width*_bpp * height // v_subs),
                   bytearray(grain.components[2].width*_bpp * height // v_subs)]
            for y in range(0, height):
                for x in range(0, grain.components[0].width):
                    bar[0][y*grain.components[0].width * _bpp + _bpp*x + 0] = pixel_ranges[grain.format][1][0] & 0xFF
                    if _bpp > 1:
                        bar[0][y*grain.components[0].width * _bpp + _bpp*x + 1] = pixel_ranges[grain.format][1][0] >> 8
            for y in range(0, height // v_subs):
                for x in range(0, grain.components[1].width):
                    bar[1][y*grain.components[1].width * _bpp + _bpp*x + 0] = pixel_ranges[grain.format][2][0] & 0xFF
                    if _bpp > 1:
                        bar[1][y*grain.components[1].width * _bpp + _bpp*x + 1] = pixel_ranges[grain.format][2][0] >> 8
                    bar[2][y*grain.components[2].width * _bpp + _bpp*x + 0] = pixel_ranges[grain.format][3][0] & 0xFF
                    if _bpp > 1:
                        bar[2][y*grain.components[2].width * _bpp + _bpp*x + 1] = pixel_ranges[grain.format][3][0] >> 8

        fnum = int(speed*grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator))

        for y in range(0, height):
            grain.data[
                grain.components[0].offset + ((fnum + y) % grain.components[0].height)*grain.components[0].stride:
                grain.components[0].offset + ((fnum + y) % grain.components[0].height)*grain.components[0].stride + grain.components[0].width*_bpp] = (
                    bar[0][y*grain.components[0].width * _bpp: (y+1)*grain.components[0].width * _bpp])
        for y in range(0, height // v_subs):
            grain.data[
                grain.components[1].offset + ((fnum//v_subs + y) % grain.components[1].height)*grain.components[1].stride:
                grain.components[1].offset + ((fnum//v_subs + y) % grain.components[1].height)*grain.components[1].stride + grain.components[1].width*_bpp] = (
                    bar[1][y*grain.components[1].width * _bpp: (y+1)*grain.components[1].width * _bpp])
            grain.data[
                grain.components[2].offset + ((fnum//v_subs + y) % grain.components[2].height)*grain.components[2].stride:
                grain.components[2].offset + ((fnum//v_subs + y) % grain.components[2].height)*grain.components[2].stride + grain.components[2].width*_bpp] = (
                    bar[2][y*grain.components[2].width * _bpp: (y+1)*grain.components[2].width * _bpp])

        yield grain


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def Tone1K(src_id, flow_id,
           samples=1920,
           channels=1,
           origin_timestamp=None,
           cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
           step=1,
           sample_rate=48000):
    return Tone(src_id, flow_id,
                1000,
                samples=samples,
                channels=channels,
                origin_timestamp=origin_timestamp,
                cog_audio_format=cog_audio_format,
                step=step,
                sample_rate=sample_rate)


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def Tone(src_id, flow_id,
         frequency,
         samples=1920,
         channels=1,
         origin_timestamp=None,
         cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
         step=1,
         sample_rate=48000):
    origin_timestamp = origin_timestamp if origin_timestamp is not None else Timestamp.get_time()
    for grain in TonePatternGenerator(
        src_id,
        flow_id,
        frequency=frequency,
        samples=samples,
        channels=channels,
        cog_audio_format=cog_audio_format,
        sample_rate=sample_rate
    )[Timestamp()::step]:
        grain.origin_timestamp = grain.origin_timestamp + origin_timestamp
        grain.sync_timestamp = grain.sync_timestamp + origin_timestamp
        yield grain


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def Silence(src_id, flow_id,
            samples=1920,
            channels=1,
            origin_timestamp=None,
            cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
            step=1,
            sample_rate=48000):
    origin_timestamp = origin_timestamp if origin_timestamp is not None else Timestamp.get_time()
    for grain in SilencePatternGenerator(
        src_id,
        flow_id,
        samples=samples,
        channels=channels,
        cog_audio_format=cog_audio_format,
        sample_rate=sample_rate
    )[Timestamp()::step]:
        grain.origin_timestamp = grain.origin_timestamp + origin_timestamp
        grain.sync_timestamp = grain.sync_timestamp + origin_timestamp
        yield grain


@deprecated(version="2.13.0", reason="Please use mediagrains.patterngenerators instead")
def AudioGrainsLoopingData(src_id, flow_id,
                           sample_data,
                           samples=1920,
                           channels=1,
                           origin_timestamp=None,
                           cog_audio_format=CogAudioFormat.S16_INTERLEAVED,
                           step=1,
                           volume=0.5,
                           sample_rate=48000):
    """
    A generator which yields audio grains of a specified format using input
    data in the form of a list of floating point values that will be repeated
    as samples indefinitely.
    """
    data_samples = {}

    if cog_audio_format in [CogAudioFormat.S16_PLANES,
                            CogAudioFormat.S16_PAIRS,
                            CogAudioFormat.S16_INTERLEAVED]:
        formatted_sample_data = [round(x*volume*(1 << 15)) for x in sample_data]
        depth = 16
    elif cog_audio_format in [CogAudioFormat.S24_PLANES,
                              CogAudioFormat.S24_PAIRS,
                              CogAudioFormat.S24_INTERLEAVED]:
        formatted_sample_data = [round(x*volume*(1 << 23)) for x in sample_data]
        depth = 24
    elif cog_audio_format in [CogAudioFormat.S32_PLANES,
                              CogAudioFormat.S32_PAIRS,
                              CogAudioFormat.S32_INTERLEAVED]:
        formatted_sample_data = [round(x*volume*(1 << 31)) for x in sample_data]
        depth = 32
    elif cog_audio_format in [CogAudioFormat.FLOAT_PLANES,
                              CogAudioFormat.FLOAT_PAIRS,
                              CogAudioFormat.FLOAT_INTERLEAVED]:
        formatted_sample_data = [x*volume for x in sample_data]
        depth = 'f'
    elif cog_audio_format in [CogAudioFormat.DOUBLE_PLANES,
                              CogAudioFormat.DOUBLE_PAIRS,
                              CogAudioFormat.DOUBLE_INTERLEAVED]:
        formatted_sample_data = [x*volume for x in sample_data]
        depth = 'd'

    planes = False
    pairs = False
    interleaved = False

    if cog_audio_format in [CogAudioFormat.S16_PLANES,
                            CogAudioFormat.S24_PLANES,
                            CogAudioFormat.S32_PLANES,
                            CogAudioFormat.FLOAT_PLANES,
                            CogAudioFormat.DOUBLE_PLANES]:
        planes = True
    elif cog_audio_format in [CogAudioFormat.S16_PAIRS,
                              CogAudioFormat.S24_PAIRS,
                              CogAudioFormat.S32_PAIRS,
                              CogAudioFormat.FLOAT_PAIRS,
                              CogAudioFormat.DOUBLE_PAIRS]:
        pairs = True
    elif cog_audio_format in [CogAudioFormat.S16_INTERLEAVED,
                              CogAudioFormat.S24_INTERLEAVED,
                              CogAudioFormat.S32_INTERLEAVED,
                              CogAudioFormat.FLOAT_INTERLEAVED,
                              CogAudioFormat.DOUBLE_INTERLEAVED]:
        interleaved = True

    rate = fractions.Fraction(sample_rate, samples)
    duration = 1/rate

    ag = AudioGrain(src_id, flow_id,
                    origin_timestamp=origin_timestamp,
                    cog_audio_format=cog_audio_format,
                    samples=samples,
                    channels=channels,
                    rate=rate,
                    duration=duration,
                    sample_rate=sample_rate)
    origin_timestamp = ag.origin_timestamp
    ots = origin_timestamp

    offs = 0
    count = 0

    def make_samples(offs, samples, channels):
        line = [formatted_sample_data[n % len(formatted_sample_data)] for n in range(offs, offs+samples)]
        if planes:
            line = line * channels
        elif pairs:
            line = [x for x in line for _ in range(0, 2)] * (channels//2)
        elif interleaved:
            line = [x for x in line for _ in range(0, channels)]

        if depth == 16:
            return struct.pack('@' + ('h'*samples*channels), *line)
        elif depth == 24:
            return b''.join(struct.pack('@i', x)[:3] for x in line)
        elif depth == 32:
            return struct.pack('@' + ('i'*samples*channels), *line)
        elif depth == 'f':
            return struct.pack('@' + ('f'*samples*channels), *line)
        elif depth == 'd':
            return struct.pack('@' + ('d'*samples*channels), *line)

    while True:
        grain = deepcopy(ag)

        grain.origin_timestamp = ots
        grain.sync_timestamp = ots

        if offs not in data_samples:
            data_samples[offs] = make_samples(offs, samples, channels)

        grain.data = bytearray(data_samples[offs][:grain.expected_length])

        yield grain

        offs = (offs + samples*step) % len(formatted_sample_data)
        count += samples*step
        ots = origin_timestamp + TimeOffset.from_count(count, sample_rate, 1)
