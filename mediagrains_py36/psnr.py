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

from mediagrains.cogenums import COG_FRAME_IS_COMPRESSED, COG_FRAME_FORMAT_ACTIVE_BITS
from mediagrains.numpy import VideoGrain as numpy_VideoGrain, VIDEOGRAIN as numpy_VIDEOGRAIN

__all__ = ["compute_psnr"]


def _compute_comp_mse(data_a, data_b):
    """Compute MSE (Mean Squared Error) for video component.

    :param data_a: Data for component a
    :param data_b: Data for component b
    :returns: The MSE value
    """
    return np.mean(np.square(np.subtract(data_a, data_b)))


def _compute_comp_psnr(data_a, data_b, max_val):
    """Compute PSNR for video component.

    :param data_a: Data for component a
    :param data_b: Data for component b
    :param max_val: Maximum value for a component pixel
    :returns: The PSNR
    """
    mse = _compute_comp_mse(data_a, data_b)
    if mse == 0:
        return float('Inf')
    else:
        return 10.0 * math.log10((max_val**2)/mse)


def compute_psnr(grain_a, grain_b):
    """Compute PSNR for video grains.

    :param grain_a: A VIDEOGRAIN
    :param grain_b: A VIDEOGRAIN
    :returns: A list of PSNR value for each video component
    """
    if grain_a.grain_type != grain_b.grain_type or grain_a.grain_type != "video":
        raise AttributeError("Invalid grain types")
    if grain_a.width != grain_b.width or grain_a.height != grain_b.height:
        raise AttributeError("Frame dimensions differ")

    if COG_FRAME_IS_COMPRESSED(grain_a.format):
        raise NotImplementedError("Compressed video is not supported")

    if not isinstance(grain_a, numpy_VIDEOGRAIN):
        grain_a = numpy_VideoGrain(grain_a)
    if not isinstance(grain_b, numpy_VIDEOGRAIN):
        grain_b = numpy_VideoGrain(grain_b)

    psnr = []
    max_val = (1 << COG_FRAME_FORMAT_ACTIVE_BITS(grain_a.format)) - 1
    for comp_data_a, comp_data_b in zip(grain_a.component_data, grain_b.component_data):
        psnr.append(_compute_comp_psnr(comp_data_a, comp_data_b, max_val))

    return psnr
