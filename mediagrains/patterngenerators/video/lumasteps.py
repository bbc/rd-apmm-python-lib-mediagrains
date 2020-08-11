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
from fractions import Fraction

from .still import StillPatternGenerator
from .constants import pixel_ranges
from ...grain_constructors import VideoGrain
from ...cogenums import CogFrameFormat, CogFrameLayout

__all__ = ["LumaSteps"]


class LumaSteps(StillPatternGenerator):
    def __init__(self, src_id, flow_id, width, height,
                 rate=Fraction(25, 1),
                 cog_frame_format=CogFrameFormat.U8_444):
        if cog_frame_format not in pixel_ranges:
            raise ValueError("Not a supported format for this generator")

        _bpp = pixel_ranges[cog_frame_format][0]
        _offset = pixel_ranges[cog_frame_format][1][0]
        _range = pixel_ranges[cog_frame_format][1][1]
        _steps = 8

        _chromaval = pixel_ranges[cog_frame_format][2][0]

        vg = VideoGrain(src_id, flow_id,
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
            vg.data[
                vg.components[0].offset +
                y*vg.components[0].stride:vg.components[0].offset +
                y*vg.components[0].stride +
                vg.components[0].width*_bpp
            ] = line

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

        super().__init__(vg)
