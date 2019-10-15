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

"""\
Library for converting video grain formats represented as numpy arrays.
"""

from mediagrains.cogenums import CogFrameFormat, CogFrameLayout
from typing import Callable, List
from uuid import uuid5, UUID
import numpy as np

from .videograin import VideoGrain, VIDEOGRAIN

__all__ = ["flow_id_for_converted_flow"]


def flow_id_for_converted_flow(source_id: UUID, fmt: CogFrameFormat) -> UUID:
    return uuid5(source_id, "FORMAT_CONVERSION: {!r}".format(fmt))


def new_grain(grain: VIDEOGRAIN, fmt: CogFrameFormat):
    return VideoGrain(grain.source_id,
                      flow_id_for_converted_flow(grain.source_id, fmt),
                      origin_timestamp=grain.origin_timestamp,
                      sync_timestamp=grain.sync_timestamp,
                      cog_frame_format=fmt,
                      width=grain.width,
                      height=grain.height,
                      rate=grain.rate,
                      duration=grain.duration,
                      cog_frame_layout=grain.layout)


# Some simple conversions can be acheived by just copying the data from one grain to the other with no
# clever work at all. All the cleverness is already present in the code that creates the component array views
# in the mediagrains
def _simple_copy_convert_yuv(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.Y[:,:] = grain_in.component_data.Y
        grain_out.component_data.U[:,:] = grain_in.component_data.U
        grain_out.component_data.V[:,:] = grain_in.component_data.V

        return grain_out
    return _inner


def _simple_copy_convert_rgb(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.R[:,:] = grain_in.component_data.R
        grain_out.component_data.G[:,:] = grain_in.component_data.G
        grain_out.component_data.B[:,:] = grain_in.component_data.B

        return grain_out
    return _inner


def _int_array_mean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """This takes the mean of two arrays of integers without risking overflowing intermediate values."""
    return (a//2 + b//2) + ((a&0x1) | (b&0x1))

# Some conversions between YUV colour subsampling systems require a simple mean
def _simple_mean_convert_yuv444__yuv422(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.Y[:,:] = grain_in.component_data.Y

        grain_out.component_data.U[:,:] = _int_array_mean(grain_in.component_data.U[0::2, :], grain_in.component_data.U[1::2, :])
        grain_out.component_data.V[:,:] = _int_array_mean(grain_in.component_data.V[0::2, :], grain_in.component_data.V[1::2, :])

        return grain_out
    return _inner


def _simple_mean_convert_yuv422__yuv420(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.Y[:,:] = grain_in.component_data.Y

        grain_out.component_data.U[:,:] = _int_array_mean(grain_in.component_data.U[:, 0::2], grain_in.component_data.U[:, 1::2])
        grain_out.component_data.V[:,:] = _int_array_mean(grain_in.component_data.V[:, 0::2], grain_in.component_data.V[:, 1::2])

        return grain_out
    return _inner

# Other conversions require duplicating samples
def _simple_duplicate_convert_yuv422__yuv444(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.Y[:,:] = grain_in.component_data.Y

        grain_out.component_data.U[0::2, :] = grain_in.component_data.U
        grain_out.component_data.U[1::2, :] = grain_in.component_data.U
        grain_out.component_data.V[0::2, :] = grain_in.component_data.V
        grain_out.component_data.V[1::2, :] = grain_in.component_data.V

        return grain_out
    return _inner

def _simple_duplicate_convert_yuv420__yuv422(fmt: CogFrameFormat) -> Callable[[VIDEOGRAIN], VIDEOGRAIN]:
    def _inner(grain_in: VIDEOGRAIN) -> VIDEOGRAIN:
        grain_out = new_grain(grain_in, fmt)

        grain_out.component_data.Y[:,:] = grain_in.component_data.Y

        grain_out.component_data.U[:, 0::2] = grain_in.component_data.U
        grain_out.component_data.U[:, 1::2] = grain_in.component_data.U
        grain_out.component_data.V[:, 0::2] = grain_in.component_data.V
        grain_out.component_data.V[:, 1::2] = grain_in.component_data.V

        return grain_out
    return _inner



def _register_simple_copy_conversions_for_formats_yuv(fmts: List[CogFrameFormat]):
    for i in range(0, len(fmts)):
        for j in range(i+1, len(fmts)):
            VIDEOGRAIN.grain_conversion(fmts[i], fmts[j])(_simple_copy_convert_yuv(fmts[j]))
            VIDEOGRAIN.grain_conversion(fmts[j], fmts[i])(_simple_copy_convert_yuv(fmts[i]))

def _register_simple_copy_conversions_for_formats_rgb(fmts: List[CogFrameFormat]):
    for i in range(0, len(fmts)):
        for j in range(i+1, len(fmts)):
            VIDEOGRAIN.grain_conversion(fmts[i], fmts[j])(_simple_copy_convert_rgb(fmts[j]))
            VIDEOGRAIN.grain_conversion(fmts[j], fmts[i])(_simple_copy_convert_rgb(fmts[i]))


# 8bit 4:2:2 YUV formats
_register_simple_copy_conversions_for_formats_yuv([
    CogFrameFormat.YUYV,
    CogFrameFormat.UYVY,
    CogFrameFormat.U8_422])

# 8 bit RGB formats
_register_simple_copy_conversions_for_formats_rgb([
    CogFrameFormat.RGB,
    CogFrameFormat.U8_444_RGB,
    CogFrameFormat.RGBx,
    CogFrameFormat.xRGB,
    CogFrameFormat.BGRx,
    CogFrameFormat.xBGR])

# 8 bit 4:4:4 YUV to 8 bit 4:2:2 YUV
for fmt in [CogFrameFormat.U8_422, CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
    VIDEOGRAIN.grain_conversion(CogFrameFormat.U8_444, fmt)(_simple_mean_convert_yuv444__yuv422(fmt))

# 8 bit 4:2:2 YUV to 8 bit 4:2:0 YUV
for fmt in [CogFrameFormat.U8_422, CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
    VIDEOGRAIN.grain_conversion(fmt, CogFrameFormat.U8_420)(_simple_mean_convert_yuv422__yuv420(CogFrameFormat.U8_420))

# 8 bit 4:4:4 YUV to 8 bit 4:2:0 YUV
VIDEOGRAIN.grain_conversion(CogFrameFormat.U8_444, CogFrameFormat.U8_420)(lambda grain: _simple_mean_convert_yuv422__yuv420(CogFrameFormat.U8_420)(_simple_mean_convert_yuv444__yuv422(CogFrameFormat.U8_422)(grain)))

# 8 bit 4:2:0 YUV to 8 bit 4:2:2 YUV
for fmt in [CogFrameFormat.U8_422, CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
    VIDEOGRAIN.grain_conversion(CogFrameFormat.U8_420, fmt)(_simple_duplicate_convert_yuv420__yuv422(fmt))

# 8 bit 4:2:0 YUV to 8 bit 4:4:4 YUV
VIDEOGRAIN.grain_conversion(CogFrameFormat.U8_420, CogFrameFormat.U8_444)(lambda grain: _simple_duplicate_convert_yuv422__yuv444(CogFrameFormat.U8_444)(_simple_duplicate_convert_yuv420__yuv422(CogFrameFormat.U8_422)(grain)))

# 8 bit 4:2:2 YUV to 8 bit 4:4:4 YUV
for fmt in [CogFrameFormat.U8_422, CogFrameFormat.UYVY, CogFrameFormat.YUYV]:
    VIDEOGRAIN.grain_conversion(fmt, CogFrameFormat.U8_444)(_simple_duplicate_convert_yuv422__yuv444(CogFrameFormat.U8_444))