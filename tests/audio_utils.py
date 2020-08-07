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

import struct

from mediagrains.cogenums import (
    CogAudioFormat,
    COG_AUDIO_FORMAT_SAMPLEBYTES,
    COG_AUDIO_IS_PLANES,
    COG_AUDIO_IS_PAIRS,
    COG_AUDIO_IS_INTERLEAVED,
    COG_AUDIO_IS_FLOAT,
    COG_AUDIO_IS_DOUBLE
)


def construct_audio_grain_data(fmt, test_data):
    """Create the bytes that would be expected in an audio grain"""
    channels = len(test_data)
    samples = len(test_data[0])

    data = bytearray()
    if fmt in [
        CogAudioFormat.S16_PLANES,
        CogAudioFormat.S16_PAIRS,
        CogAudioFormat.S16_INTERLEAVED,
        CogAudioFormat.S32_PLANES,
        CogAudioFormat.S32_PAIRS,
        CogAudioFormat.S32_INTERLEAVED
    ]:
        if COG_AUDIO_FORMAT_SAMPLEBYTES(fmt) == 2:
            pack_format = '<h'
        elif COG_AUDIO_FORMAT_SAMPLEBYTES(fmt) == 4:
            pack_format = '<i'
        elif COG_AUDIO_FORMAT_SAMPLEBYTES(fmt) == 8:
            pack_format = '<q'

        if COG_AUDIO_IS_PLANES(fmt):
            for c in range(channels):
                for s in range(samples):
                    data.extend(struct.pack(pack_format, test_data[c][s]))
        elif COG_AUDIO_IS_PAIRS(fmt):
            for cp in range((channels + 1) // 2):
                for s in range(samples):
                    data.extend(struct.pack(pack_format, test_data[cp * 2][s]))
                    if cp * 2 + 1 < channels:
                        data.extend(struct.pack(pack_format, test_data[cp * 2 + 1][s]))
                    else:
                        data.extend(struct.pack(pack_format, 0))
        elif COG_AUDIO_IS_INTERLEAVED(fmt):
            for s in range(samples):
                for c in range(channels):
                    data.extend(struct.pack(pack_format, test_data[c][s]))
    elif fmt in [
        CogAudioFormat.S24_PAIRS,
        CogAudioFormat.S24_INTERLEAVED
    ]:
        pack_format = '<i'
        if COG_AUDIO_IS_PAIRS(fmt):
            for cp in range((channels + 1) // 2):
                for s in range(samples):
                    data.extend(struct.pack(pack_format, test_data[cp * 2][s])[:3])
                    if cp * 2 + 1 < channels:
                        data.extend(struct.pack(pack_format, test_data[cp * 2 + 1][s])[:3])
                    else:
                        data.extend(struct.pack(pack_format, 0)[:3])
        elif COG_AUDIO_IS_INTERLEAVED(fmt):
            for s in range(samples):
                for c in range(channels):
                    data.extend(struct.pack(pack_format, test_data[c][s])[:3])
    elif fmt in [
        CogAudioFormat.S24_PLANES
    ]:
        pack_format = '<i'
        for c in range(channels):
            for s in range(samples):
                data.extend(struct.pack(pack_format, test_data[c][s])[:3])
                data.extend(b'\0')
    elif fmt in [
        CogAudioFormat.FLOAT_PLANES,
        CogAudioFormat.FLOAT_PAIRS,
        CogAudioFormat.FLOAT_INTERLEAVED,
        CogAudioFormat.DOUBLE_PLANES,
        CogAudioFormat.DOUBLE_PAIRS,
        CogAudioFormat.DOUBLE_INTERLEAVED
    ]:
        if COG_AUDIO_IS_FLOAT(fmt):
            pack_format = '<f'
        elif COG_AUDIO_IS_DOUBLE(fmt):
            pack_format = '<d'

        if COG_AUDIO_IS_PLANES(fmt):
            for c in range(channels):
                for s in range(samples):
                    data.extend(struct.pack(pack_format, test_data[c][s]))
        elif COG_AUDIO_IS_PAIRS(fmt):
            for cp in range((channels + 1) // 2):
                for s in range(samples):
                    data.extend(struct.pack(pack_format, test_data[cp * 2][s]))
                    if cp * 2 + 1 < channels:
                        data.extend(struct.pack(pack_format, test_data[cp * 2 + 1][s]))
                    else:
                        data.extend(struct.pack(pack_format, 0))
        elif COG_AUDIO_IS_INTERLEAVED(fmt):
            for s in range(samples):
                for c in range(channels):
                    data.extend(struct.pack(pack_format, test_data[c][s]))

    return data
