#!/usr/bin/env python3
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
"""Given a raw essence input, wrap it into a GSF file"""

from typing import Union, Type
import uuid
import argparse
import sys
import fractions

from mediatimestamp.immutable import Timestamp

from ..cogenums import CogFrameFormat, CogAudioFormat
from ..grain_constructors import VideoGrain, CodedVideoGrain, AudioGrain
from ..grain import GRAIN
from ..gsf import GSFEncoder
from ..utils import GrainWrapper, H264GrainWrapper
from ._file_or_pipe import file_or_pipe


def wrap_to_gsf(
        input_file: str,
        output_file: str,
        template_grain: GRAIN,
        Wrapper: Union[Type[GrainWrapper], Type[H264GrainWrapper]] = GrainWrapper):
    """Wrap the supplied input in GSF and write it out to a given file-like object

    :param input_file: A file path (or "-" for stdin) to read the input media from, one frame/Grain at a time
    :param output_file: A file path (or "-" for stdout) to write output GSF data to
    :param template_grain: Base Grain to use as a template for the others
    """
    with file_or_pipe(input_file, "rb") as input_data, file_or_pipe(output_file, "wb") as output_data:
        wrapper = Wrapper(template_grain, input_data)

        # Write a GSF file with the grains read from the input
        encoder = GSFEncoder(output_data)
        segment = encoder.add_segment(id=wrapper.template_grain.flow_id)
        encoder.start_dump()

        for grain in wrapper.grains():
            print("Got grain with TS {}".format(grain.origin_timestamp.to_sec_nsec()), file=sys.stderr)
            segment.add_grains([grain])

        encoder.end_dump()


def wrap_video_in_gsf():
    """Provide a utility to take a raw video input and turn it into a GSF file"""
    parser = argparse.ArgumentParser(
        description="A utility to take raw video essence and generate a GSF file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("input_file", help="Input file. Specify - for stdin", type=str)
    parser.add_argument("output_file", help="Output GSF file path. Specify - for stdout", type=str)

    parser.add_argument("--flow-id", help="UUID of GSF Flow - one will be generated if not set",
                        type=uuid.UUID, default=None)
    parser.add_argument("--source-id", help="UUID of GSF Source - one will be generated if not given",
                        type=uuid.UUID, default=None)
    parser.add_argument("--start-ts", help="Timestamp of start of media", type=Timestamp.from_str,
                        default=Timestamp(0, 0))

    parser.add_argument("--size",
                        help="Size of input uncompressed video, in WidthxHeight form, and the default for coded video",
                        default="1920x1080")

    parser.add_argument("--format", help="Frame format; one of the CogFrameFormat options",
                        type=lambda x: CogFrameFormat[x], default=CogFrameFormat.S16_422_10BIT.name)

    parser.add_argument("--rate", help="Frame rate of uncompressed input video and the default for coded video",
                        type=int, default=25)

    args = parser.parse_args()

    # Parse width and height separately
    width, height = [int(element.strip()) for element in args.size.split("x")]

    # Generate missing UUIDs
    flow_id = args.flow_id if args.flow_id else uuid.uuid4()
    source_id = args.source_id if args.source_id else uuid.uuid4()

    if args.format in [CogFrameFormat.H264, CogFrameFormat.AVCI]:
        template_grain = CodedVideoGrain(
            flow_id=flow_id, source_id=source_id, origin_timestamp=args.start_ts, rate=args.rate,
            origin_width=width, origin_height=height, coded_width=0, coded_height=0,
            cog_frame_format=args.format
        )
        Wrapper = H264GrainWrapper
    else:
        template_grain = VideoGrain(
            flow_id=flow_id, source_id=source_id, origin_timestamp=args.start_ts, rate=args.rate,
            width=width, height=height, cog_frame_format=args.format
        )
        Wrapper = GrainWrapper

    wrap_to_gsf(
        input_file=args.input_file, output_file=args.output_file, template_grain=template_grain, Wrapper=Wrapper
    )


def wrap_audio_in_gsf():
    """Provide a utility to take a raw audio input and turn it into a GSF file"""
    parser = argparse.ArgumentParser(
        description="A utility to take raw audio samples and generate a GSF file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("input_file", help="Input file. Specify - for stdin", type=str)
    parser.add_argument("output_file", help="Output GSF file path. Specify - for stdout", type=str)

    parser.add_argument("--flow-id", help="UUID of GSF Flow - one will be generated if not set",
                        type=uuid.UUID, default=None)
    parser.add_argument("--source-id", help="UUID of GSF Source - one will be generated if not given",
                        type=uuid.UUID, default=None)
    parser.add_argument("--start-ts", help="Timestamp of start of media",
                        type=Timestamp.from_str, default=Timestamp(0, 0))

    parser.add_argument("--channels", help="Number of channels present in input media", type=int, default=2)
    parser.add_argument("--samples-per-grain", help="Number of samples to write to each Grain", type=int, default=1920)

    parser.add_argument("--format", help="Audio format; one of the CogAudioFormat options",
                        type=lambda x: CogAudioFormat[x], default=CogAudioFormat.S16_PLANES.name)

    parser.add_argument("--sample-rate", help="Sample rate of input audio", type=int, default=48000)

    args = parser.parse_args()

    # Generate missing UUIDs
    flow_id = args.flow_id if args.flow_id else uuid.uuid4()
    source_id = args.source_id if args.source_id else uuid.uuid4()

    grain_rate = fractions.Fraction(args.sample_rate, args.samples_per_grain)

    template_grain = AudioGrain(
        flow_id=flow_id, source_id=source_id, origin_timestamp=args.start_ts, sample_rate=args.sample_rate,
        rate=grain_rate, channels=args.channels, samples=args.samples_per_grain, cog_audio_format=args.format
    )

    wrap_to_gsf(input_file=args.input_file, output_file=args.output_file, template_grain=template_grain)
