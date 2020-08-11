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

import math
import numpy as np

from mediagrains.cogenums import (
    COG_FRAME_IS_COMPRESSED,
    COG_FRAME_FORMAT_ACTIVE_BITS,
    COG_AUDIO_IS_FLOAT,
    COG_AUDIO_IS_DOUBLE,
    COG_AUDIO_IS_COMPRESSED,
    COG_AUDIO_FORMAT_DEPTH,
    COG_AUDIO_FORMAT_DEPTH_S16,
    COG_AUDIO_FORMAT_DEPTH_S24,
    COG_AUDIO_FORMAT_DEPTH_S32
)
from mediagrains.numpy import VideoGrain as numpy_VideoGrain, VIDEOGRAIN as numpy_VIDEOGRAIN
from mediagrains.numpy import AudioGrain as numpy_AudioGrain, AUDIOGRAIN as numpy_AUDIOGRAIN

__all__ = ["compute_psnr"]


def _compute_element_mse(data_a, data_b):
    """Compute MSE (Mean Squared Error).

    :param data_a: Data for element a
    :param data_b: Data for element b
    :returns: The MSE value
    """
    return np.mean(np.square(np.subtract(data_a, data_b, dtype=np.double)))


def _compute_element_psnr(data_a, data_b, max_val):
    """Compute PSNR.

    :param data_a: Data for a
    :param data_b: Data for b
    :param max_val: Maximum value for a component pixel
    :returns: The PSNR
    """
    mse = _compute_element_mse(data_a, data_b)
    if mse == 0:
        return float('Inf')
    else:
        return 10.0 * math.log10((max_val**2)/mse)


def _compute_audio_psnr(grain_a, grain_b, max_val=None):
    """Compute PSNR for audio grains.

    :param grain_a: An AUDIOGRAIN
    :param grain_b: An AUDIOGRAIN
    :returns: A list of PSNR values for each audio channel
    """
    if grain_a.channels != grain_b.channels:
        raise AttributeError("Channel counts differ")
    if grain_a.samples != grain_b.samples:
        raise AttributeError("Sample counts differ")

    if grain_a.format != grain_b.format:
        raise NotImplementedError("PSNR over different formats is not supported")
    if COG_AUDIO_IS_COMPRESSED(grain_a.format):
        raise NotImplementedError("Compressed audio is not supported")

    if not isinstance(grain_a, numpy_AUDIOGRAIN):
        grain_a = numpy_AudioGrain(grain_a)
    if not isinstance(grain_b, numpy_AUDIOGRAIN):
        grain_b = numpy_AudioGrain(grain_b)

    if max_val is None:
        if COG_AUDIO_IS_FLOAT(grain_a.format) or COG_AUDIO_IS_DOUBLE(grain_a.format):
            max_val = 1.0
        elif COG_AUDIO_FORMAT_DEPTH(grain_a.format) == COG_AUDIO_FORMAT_DEPTH_S16:
            max_val = 1 << 15
        elif COG_AUDIO_FORMAT_DEPTH(grain_a.format) == COG_AUDIO_FORMAT_DEPTH_S24:
            # 24-bit range was widened to 32-bit range
            max_val = 1 << 31
        elif COG_AUDIO_FORMAT_DEPTH(grain_a.format) == COG_AUDIO_FORMAT_DEPTH_S32:
            max_val = 1 << 31

    psnr = []
    for channel_data_a, channel_data_b in zip(grain_a.channel_data, grain_b.channel_data):
        psnr.append(_compute_element_psnr(channel_data_a, channel_data_b, max_val))

    return psnr


def _compute_video_psnr(grain_a, grain_b, max_val=None):
    """Compute PSNR for video grains.

    :param grain_a: A VIDEOGRAIN
    :param grain_b: A VIDEOGRAIN
    :returns: A list of PSNR values for each video component
    """
    if grain_a.width != grain_b.width or grain_a.height != grain_b.height:
        raise AttributeError("Frame dimensions differ")

    if COG_FRAME_IS_COMPRESSED(grain_a.format):
        raise NotImplementedError("Compressed video is not supported")

    if not isinstance(grain_a, numpy_VIDEOGRAIN):
        grain_a = numpy_VideoGrain(grain_a)
    if not isinstance(grain_b, numpy_VIDEOGRAIN):
        grain_b = numpy_VideoGrain(grain_b)

    if max_val is None:
        max_val = (1 << COG_FRAME_FORMAT_ACTIVE_BITS(grain_a.format)) - 1

    psnr = []
    for comp_data_a, comp_data_b in zip(grain_a.component_data, grain_b.component_data):
        psnr.append(_compute_element_psnr(comp_data_a, comp_data_b, max_val))

    return psnr


def compute_psnr(grain_a, grain_b, max_val=None):
    """Compute PSNR for video or audio grains.

    :param grain_a: A VIDEOGRAIN or AUDIOGRAIN
    :param grain_b: A VIDEOGRAIN or AUDIOGRAIN
    :param max_val: The maximum sample value
    :returns: A list of PSNR value for each video component or audio channel
    """
    if grain_a.grain_type != grain_b.grain_type:
        raise AttributeError("Grain types do not match")

    if grain_a.grain_type == "video":
        return _compute_video_psnr(grain_a, grain_b, max_val=max_val)
    elif grain_a.grain_type == "audio":
        return _compute_audio_psnr(grain_a, grain_b, max_val=max_val)
    else:
        raise AttributeError("Unsupported grain type")
