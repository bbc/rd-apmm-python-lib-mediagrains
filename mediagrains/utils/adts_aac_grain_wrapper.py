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
Support for reading ADTS AAC essence data and wrapping it in Grains.
This can be used for tasks like piping the output of ffmpeg (or similar) into a GSF file.
"""
import typing
import copy
from fractions import Fraction

from mediatimestamp.immutable import TimeRange

from ..grain import GRAIN, CODEDAUDIOGRAIN
from .adts_aac_parser import ADTSAACParser, FrameInfo, MIN_ADTS_HEADER_SIZE


class ADTSAACGrainWrapper(object):
    """Raw input and wrap it in Grains"""
    def __init__(
        self,
        template_grain: GRAIN,
        input_data: typing.IO[bytes]
    ):
        """Set up the wrapper and the Grains that will be generated

        :param template_grain: A coded audio Grain to use as the template for wrapping the Grains read from the input
                               source. origin_timestamp should be set.
        :param input_data: An object to read video data from
        """
        assert(isinstance(template_grain, CODEDAUDIOGRAIN))
        self.template_grain = copy.deepcopy(template_grain)  # make a copy as the template defaults will be updated
        self.input_data = input_data

    def _frames(self) -> typing.Iterator[typing.Tuple[bytes, FrameInfo]]:
        """Generator that yields ADTS AAC frame bytes read from the input given

        :yields: ADTS AAC frame bytes objects read from the raw input supplied and the frame info
        """
        adts_aac_parser = ADTSAACParser()

        while True:
            frame_data = self.input_data.read(MIN_ADTS_HEADER_SIZE)
            if not frame_data:
                break

            frame_info = adts_aac_parser.parse_header(frame_data)
            frame_data += self.input_data.read(frame_info.frame_size - len(frame_data))

            yield (frame_data, frame_info)

    def grains(self) -> typing.Iterator[CODEDAUDIOGRAIN]:
        """Generator that yields Grains read from the input given

        :yields: Grain objects read from the raw input supplied
        """
        frames = self._frames()

        # Parse metadata from the first frame which will override the defaults in self.template_grain
        try:
            (frame_data, frame_info) = next(frames)
        except StopIteration:
            # No frame no grain
            return
        else:
            self.template_grain.channels = frame_info.channels
            self.template_grain.sample_rate = frame_info.sample_rate
            if self.template_grain.samples is None:
                # Assuming 1024 samples per coded frame.
                # Use the --samples-per-grain option to override it to be 2048
                self.template_grain.samples = 1024

            self.template_grain.rate = Fraction(self.template_grain.sample_rate, self.template_grain.samples)
            self.template_grain.duration = 1/self.template_grain.rate

        media_rate = self.template_grain.media_rate
        coded_frame_size = self.template_grain.samples
        assert(media_rate is not None)
        assert(coded_frame_size is not None)

        norm_origin_ts = self.template_grain.origin_timestamp.normalise(media_rate.numerator, media_rate.denominator)
        grain_timerange = TimeRange.from_start(norm_origin_ts)

        frame_rate = media_rate / coded_frame_size

        for timestamp in grain_timerange.at_rate(frame_rate):
            norm_origin_ts = timestamp.normalise(media_rate.numerator, media_rate.denominator)

            new_grain = copy.deepcopy(self.template_grain)
            new_grain.origin_timestamp = norm_origin_ts
            new_grain.sync_timestamp = norm_origin_ts
            new_grain.data = frame_data

            yield new_grain

            try:
                (frame_data, frame_info) = next(frames)
            except StopIteration:
                return
