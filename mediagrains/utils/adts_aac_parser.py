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
#

"""ADTS AAC raw bitstream parser"""

MIN_ADTS_HEADER_SIZE = 7
SAMPLE_FREQUENCIES = [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350]
CHANNEL_COUNTS = [0, 1, 2, 3, 4, 5, 6, 8]


class FrameInfo(object):
    """Frame information parsed from the ADTS header"""
    def __init__(self, frame_size: int, object_type: int, sample_rate: int, channels: int):
        self.frame_size = frame_size
        self.object_type = object_type
        self.sample_rate = sample_rate
        self.channels = channels


class ADTSAACParser(object):
    def parse_header(self, frame_data: bytes) -> FrameInfo:
        """Returns the frame info if emough data is available.

        Returns None if not enough data is available to parse the header.

        :param frame_data: frame data bytes
        :returns: frame info
        :raises ValueError: if the is an issue with the bitstream
        """
        if len(frame_data) < MIN_ADTS_HEADER_SIZE:
            raise ValueError("Insufficient data size to parse the ADTS header")
        elif frame_data[0] != 0xff or (frame_data[1] & 0xf0) != 0xf0:
            raise ValueError("Missing ADTS header - invalid sync word")

        try:
            # Object type - 2 bits from bit 16
            object_type = (frame_data[2] >> 6) & 0x03
            # Sample frequency index - 4 bits from bit 18
            sample_freq_index = (frame_data[2] >> 2) & 0x0f
            sample_rate = SAMPLE_FREQUENCIES[sample_freq_index]
            # Channel config - 3 bits from bit 23
            channel_config = ((frame_data[2] & 0x01) << 2) | ((frame_data[3] >> 6) & 0x03)
            channels = CHANNEL_COUNTS[channel_config]
            # Frame size - 13 bits from bit 30
            frame_size = (
                ((frame_data[3] & 0x03) << 11) |
                (frame_data[4] << 3) |
                ((frame_data[5] >> 5) & 0x07)
            )

            frame_info = FrameInfo(frame_size, object_type, sample_rate, channels)

        except IndexError as e:
            raise ValueError from e

        return frame_info
