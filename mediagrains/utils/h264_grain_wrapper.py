# Copyright 2021 British Broadcasting Corporation
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

"""\
Support for reading H.264 essence data and wrapping it in Grains.
This can be used for tasks like piping the output of ffmpeg (or similar) into a GSF file.
"""
import typing
import copy
from math import ceil

from mediatimestamp.immutable import TimeRange

from ..grain import GRAIN, CODEDVIDEOGRAIN
from .h264_parser import H264Parser, FrameInfo

# Read in blocks of 8K
READ_BLOCK_SIZE = 8192


class H264GrainWrapper(object):
    """Raw input and wrap it in Grains"""
    def __init__(
        self,
        template_grain: GRAIN,
        input_data: typing.IO[bytes]
    ):
        """Set up the wrapper and the Grains that will be generated

        :param template_grain: A coded video Grain to use as the template for wrapping the Grains read from the input source.
                               origin_timestamp should be set.
        :param input_data: An object to read video data from
        """
        assert(isinstance(template_grain, CODEDVIDEOGRAIN))
        self.template_grain = copy.deepcopy(template_grain)  # make a copy as the template defaults will be updated
        self.input_data = input_data
        self.input_data_buffer = bytearray()

    def _frames(self) -> typing.Iterator[typing.Tuple[bytes, typing.List[int], typing.Optional[FrameInfo]]]:
        """Generator that yields H.264 frame bytes read from the input given

        :yields: H.264 frame bytes objects read from the raw input supplied
        """
        h264_parser = H264Parser()

        end_of_input_data = False
        prev_frame_size = None
        while not end_of_input_data:
            # Parse the frame. The frame size is determined by detecting the start of the next frame
            start_of_new_frame = True
            while True:
                # Estimate how much to read based on the previous frame size and default to 8K
                read_size = 0
                if start_of_new_frame:
                    if prev_frame_size is not None:
                        if prev_frame_size > len(self.input_data_buffer):
                            read_size = prev_frame_size - len(self.input_data_buffer)
                            read_size = ceil(read_size / READ_BLOCK_SIZE) * READ_BLOCK_SIZE
                    elif len(self.input_data_buffer) == 0:
                        read_size = READ_BLOCK_SIZE
                    start_of_new_frame = False
                else:
                    read_size = READ_BLOCK_SIZE

                if read_size > 0:
                    data = self.input_data.read(read_size)
                    if data:
                        self.input_data_buffer += data

                (frame_size, nalu_byte_offsets, frame_info) = h264_parser.parse_frame(self.input_data_buffer)

                if frame_size is not None:
                    # Parsed a new frame
                    prev_frame_size = frame_size
                    break
                elif read_size > 0 and not data:
                    # No frame parsed and no more data to read. Assume the remainder is the last frame
                    end_of_input_data = True
                    break

            if frame_size is not None and frame_size > 0:
                assert(nalu_byte_offsets is not None)

                frame_data = self.input_data_buffer[:frame_size]
                yield (frame_data, list(nalu_byte_offsets), frame_info)

                self.input_data_buffer = self.input_data_buffer[frame_size:]

        # Assume the remainder is a frame an yield it if there are NAL units
        if len(self.input_data_buffer) > 0:
            frame_data = self.input_data_buffer
            unit_offsets = list(h264_parser.get_nalu_byte_offsets(frame_data))
            if len(unit_offsets) > 0:
                frame_info = h264_parser.parse_frame_info(frame_data, nalu_byte_offsets=unit_offsets)
                yield (frame_data, unit_offsets, frame_info)

    def grains(self) -> typing.Iterator[CODEDVIDEOGRAIN]:
        """Generator that yields Grains read from the input given

        :yields: Grain objects read from the raw input supplied
        """
        frames = self._frames()

        # Parse metadata from the first frame which will override the defaults in self.template_grain
        # WARNING: this means the first H.264 frame should contain the metadata (in SPS+PPS)
        # because otherwise the defaults could be wrong
        try:
            (frame_data, unit_offsets, frame_info) = next(frames)
        except StopIteration:
            # No frame no grain
            return
        else:
            if frame_info is not None:
                if frame_info.width is not None:
                    self.template_grain.origin_width = frame_info.width
                    if frame_info.coded_width is not None:
                        self.template_grain.coded_width = frame_info.coded_width
                    else:
                        self.template_grain.coded_width = 0
                if frame_info.height is not None:
                    self.template_grain.origin_height = frame_info.height
                    if frame_info.coded_height is not None:
                        self.template_grain.coded_height = frame_info.coded_height
                    else:
                        self.template_grain.coded_height = 0
                if frame_info.frame_rate is not None:
                    self.template_grain.rate = frame_info.frame_rate

        rate = self.template_grain.rate
        norm_origin_ts = self.template_grain.origin_timestamp.normalise(rate.numerator, rate.denominator)
        grain_timerange = TimeRange.from_start(norm_origin_ts)

        for timestamp in grain_timerange.at_rate(rate):
            norm_origin_ts = timestamp.normalise(rate.numerator, rate.denominator)

            new_grain = copy.deepcopy(self.template_grain)
            new_grain.origin_timestamp = norm_origin_ts
            if frame_info is not None and frame_info.key_frame is not None:
                new_grain.is_key_frame = frame_info.key_frame
            else:
                new_grain.is_key_frame = False
            new_grain.temporal_offset = 0  # Not parsed
            new_grain.unit_offsets = unit_offsets  # type: ignore
            new_grain.data = frame_data

            yield new_grain

            try:
                (frame_data, unit_offsets, frame_info) = next(frames)
            except StopIteration:
                return
