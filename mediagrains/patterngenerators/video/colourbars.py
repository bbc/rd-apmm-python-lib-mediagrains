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

from ...grain_constructors import VideoGrain
from .constants import pixel_ranges
from .still import StillPatternGenerator
from ...cogenums import CogFrameFormat, CogFrameLayout

__all__ = ["ColourBars"]


class ColourBars(StillPatternGenerator):
    def __init__(self, src_id, flow_id, width, height,
                 intensity=0.75,
                 rate=Fraction(25, 1),
                 cog_frame_format=CogFrameFormat.U8_444):
        if cog_frame_format not in pixel_ranges:
            raise ValueError("Not a supported format for this generator")

        _bpp = pixel_ranges[cog_frame_format][0]
        _steps = 8
        bs = 16 - pixel_ranges[cog_frame_format][4]

        values = [
            (int((0xFFFF >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs),
            (int((0xE1FF >> bs) * intensity), 0x0000 >> bs, 0x9400 >> bs),
            (int((0xB200 >> bs) * intensity), 0xABFF >> bs, 0x0000 >> bs),
            (int((0x95FF >> bs) * intensity), 0x2BFF >> bs, 0x15FF >> bs),
            (int((0x69FF >> bs) * intensity), 0xD400 >> bs, 0xEA00 >> bs),
            (int((0x4C00 >> bs) * intensity), 0x5400 >> bs, 0xFFFF >> bs),
            (int((0x1DFF >> bs) * intensity), 0xFFFF >> bs, 0x6BFF >> bs),
            (int((0x0000 >> bs) * intensity), 0x8000 >> bs, 0x8000 >> bs)]

        vg = VideoGrain(src_id, flow_id,
                        rate=rate,
                        cog_frame_format=cog_frame_format,
                        cog_frame_layout=CogFrameLayout.FULL_FRAME,
                        width=width,
                        height=height)

        lines = [bytearray(vg.components[0].width*_bpp), bytearray(vg.components[1].width*_bpp), bytearray(vg.components[2].width*_bpp)]
        for c in range(0, 3):
            for x in range(0, vg.components[c].width):
                pos = x//(vg.components[c].width//_steps)
                if _bpp == 1:
                    lines[c][x] = values[pos][c]
                elif _bpp == 2:
                    lines[c][2*x + 0] = values[pos][c] & 0xFF
                    lines[c][2*x + 1] = (values[pos][c] >> 8) & 0xFF

        for c in range(0, 3):
            for y in range(0, vg.components[c].height):
                vg.data[vg.components[c].offset +
                        y*vg.components[c].stride:vg.components[c].offset +
                        y*vg.components[c].stride +
                        vg.components[c].width*_bpp] = lines[c]

        super().__init__(vg)
