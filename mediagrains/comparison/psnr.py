#!/usr/bin/python
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

from __future__ import print_function
from __future__ import absolute_import

from sys import version_info

if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    from mediagrains_py36.psnr import compute_psnr

    __all__ = ["compute_psnr"]

else:
    import math
    import numpy as np

    from ..cogenums import COG_FRAME_FORMAT_BYTES_PER_VALUE, COG_FRAME_FORMAT_ACTIVE_BITS
    from ..cogenums import COG_FRAME_IS_COMPRESSED, COG_FRAME_IS_PACKED

    __all__ = ["compute_psnr"]


    def _compute_comp_mse(format, data_a, comp_a, data_b, comp_b):
        """Compute MSE (Mean Squared Error) for video component.

        Currently supports planar components only.

        :param format: The COG format
        :param data_a: Data bytes for GRAIN component a
        :param comp_a: COMPONENT for GRAIN a
        :param data_b: Data bytes for GRAIN component b
        :param comp_b: COMPONENT for GRAIN b
        :returns: The MSE value
        """
        if COG_FRAME_IS_PACKED(format):
            raise NotImplementedError("Packed video format is not supported in this version of python")

        bpp = COG_FRAME_FORMAT_BYTES_PER_VALUE(format)
        if bpp == 1:
            dtype = np.uint8
        elif bpp == 2:
            dtype = np.uint16
        elif bpp == 4:
            dtype = np.uint32

        total = 0
        for y in range(0, comp_a.height):
            line_a = data_a[y*comp_a.stride + comp_a.offset:y*comp_a.stride + comp_a.offset + comp_a.width*bpp]
            line_b = data_b[y*comp_b.stride + comp_b.offset:y*comp_b.stride + comp_b.offset + comp_b.width*bpp]
            np_line_a = np.frombuffer(line_a, dtype=dtype)
            np_line_b = np.frombuffer(line_b, dtype=dtype)
            total += np.sum(np.square(np.subtract(np_line_a, np_line_b)))

        return total / (comp_a.width*comp_a.height)


    def _compute_comp_psnr(format, data_a, comp_a, data_b, comp_b, max_val):
        """Compute PSNR for video component.

        Currently supports planar components only.

        :param format: The COG format
        :param data_a: Data bytes for GRAIN component a
        :param comp_a: COMPONENT for GRAIN a
        :param data_b: Data bytes for GRAIN component b
        :param comp_b: COMPONENT for GRAIN b
        :param max_val: Maximum value for a component pixel
        :returns: The PSNR
        """
        mse = _compute_comp_mse(format, data_a, comp_a, data_b, comp_b)
        if mse == 0:
            return float('Inf')
        else:
            return 10.0 * math.log10((max_val**2)/mse)


    def compute_psnr(grain_a, grain_b):
        """Compute PSNR for video grains.

        :param grain_a: A video GRAIN
        :param grain_b: A video GRAIN
        :returns: A list of PSNR value for each video component
        """
        if grain_a.grain_type != grain_b.grain_type or grain_a.grain_type != "video":
            raise AttributeError("Invalid grain types")
        if grain_a.width != grain_b.width or grain_a.height != grain_b.height:
            raise AttributeError("Frame dimensions differ")

        if grain_a.format != grain_b.format:
            raise NotImplementedError("Different grain formats not supported")
        if COG_FRAME_IS_COMPRESSED(grain_a.format):
            raise NotImplementedError("Compressed video is not supported")

        psnr = []
        data_a = bytes(grain_a.data)
        data_b = bytes(grain_b.data)
        max_val = (1 << COG_FRAME_FORMAT_ACTIVE_BITS(grain_a.format)) - 1
        for comp_a, comp_b in zip(grain_a.components, grain_b.components):
            psnr.append(_compute_comp_psnr(grain_a.format, data_a, comp_a, data_b, comp_b, max_val))

        return psnr
