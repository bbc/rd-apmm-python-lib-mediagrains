#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
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
The submodule of mediagrains which contains code for generating test video
grains.
"""

from __future__ import print_function
from __future__ import absolute_import

__all__ = ["LumaSteps"]

from fractions import Fraction
from mediatimestamp import TimeOffset
from copy import deepcopy

from . import VideoGrain
from .cogenums import CogFrameFormat, CogFrameLayout


# information about formats
# in the order:
# (num_bytes_per_sample, (offset, range), (offset, range), (offset, range))
# in YUV order
pixel_ranges = {
    CogFrameFormat.U8_444: (1, (16, 235-16), (128, 224), (128, 224)),
    CogFrameFormat.U8_422: (1, (16, 235-16), (128, 224), (128, 224)),
    CogFrameFormat.U8_420: (1, (16, 235-16), (128, 224), (128, 224)),
    CogFrameFormat.S16_444_10BIT: (2, (64, 940-64), (512, 896), (512, 896)),
    CogFrameFormat.S16_422_10BIT: (2, (64, 940-64), (512, 896), (512, 896)),
    CogFrameFormat.S16_420_10BIT: (2, (64, 940-64), (512, 896), (512, 896)),
    CogFrameFormat.S16_444_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584)),
    CogFrameFormat.S16_422_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584)),
    CogFrameFormat.S16_420_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584)),
    CogFrameFormat.S16_444: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344)),
    CogFrameFormat.S16_422: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344)),
    CogFrameFormat.S16_420: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344)),
}


def LumaSteps(src_id, flow_id, width, height,
              rate=Fraction(25, 1),
              origin_timestamp=None,
              cog_frame_format=CogFrameFormat.U8_444,
              step=1):
    """Returns a generator for video grains in U8_444 format.
    :param src_id: source_id for grains
    :param flow_id: flow_id for grains
    :param width: width of grains
    :param height: height of grains
    :param rate: rate of grains
    :param origin_timestamp: the origin timestamp of the first grain.
    :param step: The number of grains to increment by each time (values above 1 cause skipping)"""

    if cog_frame_format not in pixel_ranges:
        raise ValueError("Not a supported format for this generator")

    _bpp = pixel_ranges[cog_frame_format][0]
    _offset = pixel_ranges[cog_frame_format][1][0]
    _range = pixel_ranges[cog_frame_format][1][1]
    _steps = 8

    _chromaval = pixel_ranges[cog_frame_format][2][0]

    vg = VideoGrain(src_id, flow_id, origin_timestamp=origin_timestamp,
                    rate=rate,
                    cog_frame_format=cog_frame_format,
                    cog_frame_layout=CogFrameLayout.FULL_FRAME,
                    width=width,
                    height=height)

    line = bytearray(width*_bpp)
    for x in range(0, width):
        pos = x//(width//_steps)
        if _bpp == 1:
            line[x] = (_offset + ((pos * _range)//_steps)) & 0xFF
        elif _bpp == 2:
            line[2*x + 0] = (_offset + ((pos * _range)//_steps)) & 0xFF
            line[2*x + 1] = ((_offset + ((pos * _range)//_steps)) >> 8) & 0xFF

    for y in range(0, height):
        vg.data[vg.components[0].offset + y*vg.components[0].stride:vg.components[0].offset + y*vg.components[0].stride + vg.components[0].width*_bpp] = line

    if _bpp == 1:
        for y in range(0, vg.components[1].height):
            u = vg.components[1].offset + y*vg.components[1].stride
            v = vg.components[2].offset + y*vg.components[2].stride
            for x in range(0, vg.components[1].width):
                vg.data[u + x] = _chromaval
                vg.data[v + x] = _chromaval
    else:
        for y in range(0, vg.components[1].height):
            u = vg.components[1].offset + y*vg.components[1].stride
            v = vg.components[2].offset + y*vg.components[2].stride
            for x in range(0, vg.components[1].width):
                vg.data[u + 2*x + 0] = _chromaval & 0xFF
                vg.data[u + 2*x + 1] = (_chromaval >> 8) & 0xFF
                vg.data[v + 2*x + 0] = _chromaval & 0xFF
                vg.data[v + 2*x + 1] = (_chromaval >> 8) & 0xFF

    origin_timestamp = vg.origin_timestamp
    count = 0
    while True:
        yield deepcopy(vg)
        count += step
        vg.origin_timestamp = origin_timestamp + TimeOffset.from_count(count,
                                                                       rate.numerator, rate.denominator)
        vg.sync_timestamp = vg.origin_timestamp
