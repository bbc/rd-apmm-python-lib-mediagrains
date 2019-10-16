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

from mediagrains.cogenums import CogFrameFormat, CogFrameLayout, COG_FRAME_FORMAT_ACTIVE_BITS, COG_PLANAR_FORMAT, PlanarChromaFormat
from typing import Callable, List
from uuid import uuid5, UUID
import numpy as np
import numpy.random as npr

from pdb import set_trace

from .videograin import VideoGrain, VIDEOGRAIN


def distinct_pairs_from(vals):
    for i in range(0, len(vals)):
        for j in range(i + 1, len(vals)):
            yield (vals[i], vals[j])


def compose(first: Callable[[VIDEOGRAIN, VIDEOGRAIN], None], intermediate: CogFrameFormat, second: Callable[[VIDEOGRAIN, VIDEOGRAIN], None]) -> Callable[[VIDEOGRAIN, VIDEOGRAIN], None]:
    """Compose two conversion functions together"""
    def _inner(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
        grain_intermediate = grain_in._similar_grain(intermediate)

        first(grain_in, grain_intermediate)
        second(grain_intermediate, grain_out)
    return _inner


# Some simple conversions can be acheived by just copying the data from one grain to the other with no
# clever work at all. All the cleverness is already present in the code that creates the component array views
# in the mediagrains
def _simple_copy_convert_yuv(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.Y[:,:] = grain_in.component_data.Y
    grain_out.component_data.U[:,:] = grain_in.component_data.U
    grain_out.component_data.V[:,:] = grain_in.component_data.V


def _simple_copy_convert_rgb(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.R[:,:] = grain_in.component_data.R
    grain_out.component_data.G[:,:] = grain_in.component_data.G
    grain_out.component_data.B[:,:] = grain_in.component_data.B


def _int_array_mean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """This takes the mean of two arrays of integers without risking overflowing intermediate values."""
    return (a//2 + b//2) + ((a&0x1) | (b&0x1))


# Some conversions between YUV colour subsampling systems require a simple mean
def _simple_mean_convert_yuv444__yuv422(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.Y[:,:] = grain_in.component_data.Y
    grain_out.component_data.U[:,:] = _int_array_mean(grain_in.component_data.U[0::2, :], grain_in.component_data.U[1::2, :])
    grain_out.component_data.V[:,:] = _int_array_mean(grain_in.component_data.V[0::2, :], grain_in.component_data.V[1::2, :])


def _simple_mean_convert_yuv422__yuv420(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.Y[:,:] = grain_in.component_data.Y
    grain_out.component_data.U[:,:] = _int_array_mean(grain_in.component_data.U[:, 0::2], grain_in.component_data.U[:, 1::2])
    grain_out.component_data.V[:,:] = _int_array_mean(grain_in.component_data.V[:, 0::2], grain_in.component_data.V[:, 1::2])


# Other conversions require duplicating samples
def _simple_duplicate_convert_yuv422__yuv444(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.Y[:,:] = grain_in.component_data.Y

    grain_out.component_data.U[0::2, :] = grain_in.component_data.U
    grain_out.component_data.U[1::2, :] = grain_in.component_data.U
    grain_out.component_data.V[0::2, :] = grain_in.component_data.V
    grain_out.component_data.V[1::2, :] = grain_in.component_data.V


def _simple_duplicate_convert_yuv420__yuv422(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    grain_out.component_data.Y[:,:] = grain_in.component_data.Y

    grain_out.component_data.U[:, 0::2] = grain_in.component_data.U
    grain_out.component_data.U[:, 1::2] = grain_in.component_data.U
    grain_out.component_data.V[:, 0::2] = grain_in.component_data.V
    grain_out.component_data.V[:, 1::2] = grain_in.component_data.V


# Bit depth conversions
def _unbiased_right_shift(a: np.ndarray, n: int) -> np.ndarray:
    return (a >> n) + ((a >> (n - 1))&0x1)

def _bitdepth_down_convert_yuv(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bitshift = COG_FRAME_FORMAT_ACTIVE_BITS(grain_in.format) - COG_FRAME_FORMAT_ACTIVE_BITS(grain_out.format)

    grain_out.component_data[0][:] = _unbiased_right_shift(grain_in.component_data[0][:], bitshift)
    grain_out.component_data[1][:] = _unbiased_right_shift(grain_in.component_data[1][:], bitshift)
    grain_out.component_data[2][:] = _unbiased_right_shift(grain_in.component_data[2][:], bitshift)

def _bitdepth_down_convert_rgb(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bitshift = COG_FRAME_FORMAT_ACTIVE_BITS(grain_in.format) - COG_FRAME_FORMAT_ACTIVE_BITS(grain_out.format)

    grain_out.component_data.R[:] = _unbiased_right_shift(grain_in.component_data.R[:], bitshift)
    grain_out.component_data.G[:] = _unbiased_right_shift(grain_in.component_data.G[:], bitshift)
    grain_out.component_data.B[:] = _unbiased_right_shift(grain_in.component_data.B[:], bitshift)


def _noisy_left_shift(a: np.ndarray, n: int) -> np.ndarray:
    rando = ((npr.random_sample(a.shape) * (1 << n)).astype(a.dtype)) & ((1 << n) - 1)
    return (a << n) + rando

def _bitdepth_up_convert_yuv(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bitshift = COG_FRAME_FORMAT_ACTIVE_BITS(grain_out.format) - COG_FRAME_FORMAT_ACTIVE_BITS(grain_in.format)

    dt = grain_out.component_data[0].dtype

    grain_out.component_data[0][:] = _noisy_left_shift(grain_in.component_data[0][:].astype(dt), bitshift)
    grain_out.component_data[1][:] = _noisy_left_shift(grain_in.component_data[1][:].astype(dt), bitshift)
    grain_out.component_data[2][:] = _noisy_left_shift(grain_in.component_data[2][:].astype(dt), bitshift)

def _bitdepth_up_convert_rgb(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bitshift = COG_FRAME_FORMAT_ACTIVE_BITS(grain_out.format) - COG_FRAME_FORMAT_ACTIVE_BITS(grain_in.format)

    dt = grain_out.component_data[0].dtype

    grain_out.component_data.R[:] = _noisy_left_shift(grain_in.component_data.R[:].astype(dt), bitshift)
    grain_out.component_data.G[:] = _noisy_left_shift(grain_in.component_data.G[:].astype(dt), bitshift)
    grain_out.component_data.B[:] = _noisy_left_shift(grain_in.component_data.B[:].astype(dt), bitshift)


# Colourspace conversions (based on rec.709)
def _convert_rgb_to_yuv444(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bd = COG_FRAME_FORMAT_ACTIVE_BITS(grain_out.format)
    (R, G, B) = (grain_in.component_data.R,
                    grain_in.component_data.G,
                    grain_in.component_data.B)

    grain_out.component_data.Y[:,:] = (R*0.2126 +  G*0.7152 + B*0.0722)
    grain_out.component_data.U[:,:] = (R*-0.114572 - G*0.385428 + B*0.5 + (1 << (bd - 1)))
    grain_out.component_data.V[:,:] = (R*0.5 - G*0.454153 - B*0.045847  + (1 << (bd - 1)))


def _convert_yuv444_to_rgb(grain_in: VIDEOGRAIN, grain_out: VIDEOGRAIN):
    bd = COG_FRAME_FORMAT_ACTIVE_BITS(grain_in.format)
    (Y, U, V) = (grain_in.component_data.Y.astype(np.dtype(np.double)),
                    grain_in.component_data.U.astype(np.dtype(np.double)) - (1 << (bd - 1)),
                    grain_in.component_data.V.astype(np.dtype(np.double)) - (1 << (bd - 1)))

    grain_out.component_data.R[:,:] = (Y + V*1.5748)
    grain_out.component_data.G[:,:] = (Y - U*0.187324 - V*0.468124)
    grain_out.component_data.B[:,:] = (Y + U*1.8556)


# These methods automate the process of registering simple copy conversions
def _register_simple_copy_conversions_for_formats_yuv(fmts: List[CogFrameFormat]):
    for i in range(0, len(fmts)):
        for j in range(i+1, len(fmts)):
            VIDEOGRAIN.grain_conversion(fmts[i], fmts[j])(_simple_copy_convert_yuv)
            VIDEOGRAIN.grain_conversion(fmts[j], fmts[i])(_simple_copy_convert_yuv)

def _register_simple_copy_conversions_for_formats_rgb(fmts: List[CogFrameFormat]):
    for i in range(0, len(fmts)):
        for j in range(i+1, len(fmts)):
            VIDEOGRAIN.grain_conversion(fmts[i], fmts[j])(_simple_copy_convert_rgb)
            VIDEOGRAIN.grain_conversion(fmts[j], fmts[i])(_simple_copy_convert_rgb)


def _equivalent_formats(fmt: CogFrameFormat) -> List[CogFrameFormat]:
    equiv_categories = [
        (CogFrameFormat.U8_422, CogFrameFormat.UYVY, CogFrameFormat.YUYV),
        (CogFrameFormat.S16_422, CogFrameFormat.v216),
        (CogFrameFormat.RGB, CogFrameFormat.U8_444_RGB, CogFrameFormat.RGBx, CogFrameFormat.xRGB, CogFrameFormat.BGRx, CogFrameFormat.xBGR)]

    for cat in equiv_categories:
        if fmt in cat:
            return cat
    return (fmt,)


_register_simple_copy_conversions_for_formats_yuv(_equivalent_formats(CogFrameFormat.U8_422))
_register_simple_copy_conversions_for_formats_yuv(_equivalent_formats(CogFrameFormat.S16_422))
_register_simple_copy_conversions_for_formats_rgb(_equivalent_formats(CogFrameFormat.U8_444_RGB))

# 8 and 16 bit YUV colour subsampling conversions
for bd in [8, 10, 12, 16, 32]:
    for fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_422, bd)):
        VIDEOGRAIN.grain_conversion(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, bd), fmt)(_simple_mean_convert_yuv444__yuv422)
        VIDEOGRAIN.grain_conversion(fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_420, bd))(_simple_mean_convert_yuv422__yuv420)
        VIDEOGRAIN.grain_conversion(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_420, bd), fmt)(_simple_duplicate_convert_yuv420__yuv422)
        VIDEOGRAIN.grain_conversion(fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, bd))(_simple_duplicate_convert_yuv422__yuv444)
    VIDEOGRAIN.grain_conversion(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, bd), COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_420, bd))(compose(_simple_mean_convert_yuv444__yuv422, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_422, bd), _simple_mean_convert_yuv422__yuv420))
    VIDEOGRAIN.grain_conversion(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_420, bd), COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, bd))(compose(_simple_duplicate_convert_yuv420__yuv422, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_422, bd), _simple_duplicate_convert_yuv422__yuv444))


# Bit depth conversions
for (d1, d2) in distinct_pairs_from([8, 10, 12, 16, 32]):
    for ss in [PlanarChromaFormat.YUV_420, PlanarChromaFormat.YUV_422, PlanarChromaFormat.YUV_444]:
        for fmt1 in _equivalent_formats(COG_PLANAR_FORMAT(ss, d1)):
            for fmt2 in _equivalent_formats(COG_PLANAR_FORMAT(ss, d2)):
                VIDEOGRAIN.grain_conversion(fmt2, fmt1)(_bitdepth_down_convert_yuv)
                VIDEOGRAIN.grain_conversion(fmt1, fmt2)(_bitdepth_up_convert_yuv)
    for ss in [PlanarChromaFormat.RGB]:
        for fmt1 in _equivalent_formats(COG_PLANAR_FORMAT(ss, d1)):
            for fmt2 in _equivalent_formats(COG_PLANAR_FORMAT(ss, d2)):
                VIDEOGRAIN.grain_conversion(fmt2, fmt1)(_bitdepth_down_convert_rgb)
                VIDEOGRAIN.grain_conversion(fmt1, fmt2)(_bitdepth_up_convert_rgb)


# Colourspace conversion
for d in [8, 10, 12, 16, 32]:
    for fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d)):
        VIDEOGRAIN.grain_conversion(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d), fmt)(_convert_yuv444_to_rgb)
        VIDEOGRAIN.grain_conversion(fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d))(_convert_rgb_to_yuv444)


# We have a number of transformations that aren't supported directly, but are via an intermediate format
# Bit depth and chroma combination conversions
for (ss1, ss2) in distinct_pairs_from([PlanarChromaFormat.YUV_420, PlanarChromaFormat.YUV_422, PlanarChromaFormat.YUV_444]):
    for (d1, d2) in distinct_pairs_from([8, 10, 12, 16, 32]):
        for fmt11 in _equivalent_formats(COG_PLANAR_FORMAT(ss1, d1)):
            for fmt22 in _equivalent_formats(COG_PLANAR_FORMAT(ss2, d2)):
                VIDEOGRAIN.grain_conversion_two_step(fmt11, COG_PLANAR_FORMAT(ss2, d1), fmt22)
                VIDEOGRAIN.grain_conversion_two_step(fmt22, COG_PLANAR_FORMAT(ss1, d2), fmt11)
        for fmt12 in _equivalent_formats(COG_PLANAR_FORMAT(ss1, d2)):
            for fmt21 in _equivalent_formats(COG_PLANAR_FORMAT(ss2, d1)):
                VIDEOGRAIN.grain_conversion_two_step(fmt12, COG_PLANAR_FORMAT(ss2, d2), fmt21)
                VIDEOGRAIN.grain_conversion_two_step(fmt21, COG_PLANAR_FORMAT(ss2, d2), fmt12)

# RGB and non-444 YUV at same bit-depth
for d in [8, 10, 12, 16, 32]:
    for rgb_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d)):
        for ss in [PlanarChromaFormat.YUV_420, PlanarChromaFormat.YUV_422]:
            for yuv_fmt in _equivalent_formats(COG_PLANAR_FORMAT(ss, d)):
                VIDEOGRAIN.grain_conversion_two_step(rgb_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d), yuv_fmt)
                VIDEOGRAIN.grain_conversion_two_step(yuv_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d), rgb_fmt)

# RGB and YUV-444 with bit-depth conversion
for (d1, d2) in distinct_pairs_from([8, 10, 12, 16, 32]):
    for rgb_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d1)):
        for yuv_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d2)):
            VIDEOGRAIN.grain_conversion_two_step(rgb_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d1), yuv_fmt)
            VIDEOGRAIN.grain_conversion_two_step(yuv_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d2), rgb_fmt)
    for rgb_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d2)):
        for yuv_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d1)):
            VIDEOGRAIN.grain_conversion_two_step(rgb_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d2), yuv_fmt)
            VIDEOGRAIN.grain_conversion_two_step(yuv_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d1), rgb_fmt)

# RGB to YUV with bit-depth and colour subsampling conversion
for (d1, d2) in distinct_pairs_from([8, 10, 12, 16, 32]):
    for ss in [PlanarChromaFormat.YUV_420, PlanarChromaFormat.YUV_422]:
        for rgb_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d1)):
            for yuv_fmt in _equivalent_formats(COG_PLANAR_FORMAT(ss, d2)):
                VIDEOGRAIN.grain_conversion_two_step(rgb_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d1), yuv_fmt)
                VIDEOGRAIN.grain_conversion_two_step(yuv_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d1), rgb_fmt)
        for rgb_fmt in _equivalent_formats(COG_PLANAR_FORMAT(PlanarChromaFormat.RGB, d2)):
            for yuv_fmt in _equivalent_formats(COG_PLANAR_FORMAT(ss, d1)):
                VIDEOGRAIN.grain_conversion_two_step(rgb_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d2), yuv_fmt)
                VIDEOGRAIN.grain_conversion_two_step(yuv_fmt, COG_PLANAR_FORMAT(PlanarChromaFormat.YUV_444, d2), rgb_fmt)