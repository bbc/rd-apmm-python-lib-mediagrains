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

from typing import Optional, cast
from mediatimestamp import TimeValue

from ...grain import VIDEOGRAIN
from .abc import VideoPatternGenerator
from .constants import pixel_ranges
from ...cogenums import COG_FRAME_FORMAT_H_SHIFT, COG_FRAME_FORMAT_V_SHIFT


__all__ = ["MovingBarOverlay"]


class MovingBarOverlay (VideoPatternGenerator):
    def __init__(self, source: VideoPatternGenerator, height=100, speed=1.0):
        super().__init__(
            src_id=source.src_id,
            flow_id=source.flow_id,
            width=source.width,
            height=source.height,
            rate=source.rate,
            cog_frame_format=source.cog_frame_format)
        self._source = source
        self._bar_height = height
        self._bar_speed = speed

        if self.cog_frame_format not in pixel_ranges:
            raise ValueError("Not a supported format for this generator")

        _bpp = pixel_ranges[self.cog_frame_format][0]

        h_shift = COG_FRAME_FORMAT_H_SHIFT(self.cog_frame_format)
        v_shift = COG_FRAME_FORMAT_V_SHIFT(self.cog_frame_format)

        bar = [bytearray(self.width*_bpp * height),
               bytearray((self.width >> h_shift)*_bpp * (height >> v_shift)),
               bytearray((self.width >> h_shift)*_bpp * (height >> v_shift))]
        for y in range(0, height):
            for x in range(0, self.width):
                bar[0][y*self.width*_bpp + _bpp*x + 0] = pixel_ranges[self.cog_frame_format][1][0] & 0xFF
                if _bpp > 1:
                    bar[0][y*self.width*_bpp + _bpp*x + 1] = pixel_ranges[self.cog_frame_format][1][0] >> 8
        for y in range(0, (height >> v_shift)):
            for x in range(0, self.width >> h_shift):
                bar[1][y*(self.width >> h_shift)*_bpp + _bpp*x + 0] = pixel_ranges[self.cog_frame_format][2][0] & 0xFF
                if _bpp > 1:
                    bar[1][y*(self.width >> h_shift)*_bpp + _bpp*x + 1] = pixel_ranges[self.cog_frame_format][2][0] >> 8
                bar[2][y*(self.width >> h_shift)*_bpp + _bpp*x + 0] = pixel_ranges[self.cog_frame_format][3][0] & 0xFF
                if _bpp > 1:
                    bar[2][y*(self.width >> h_shift)*_bpp + _bpp*x + 1] = pixel_ranges[self.cog_frame_format][3][0] >> 8

        self._bar = bar

    def get(self, key: TimeValue, default: Optional[VIDEOGRAIN] = None) -> Optional[VIDEOGRAIN]:
        tv = TimeValue(key, rate=self.rate)

        grain = self._source[tv]

        if grain is not None:
            fnum = int(self._bar_speed*grain.origin_timestamp.to_count(grain.rate.numerator, grain.rate.denominator))
            _bpp = pixel_ranges[self.cog_frame_format][0]
            v_shift = COG_FRAME_FORMAT_V_SHIFT(self.cog_frame_format)

            for y in range(0, self._bar_height):
                line_no = ((fnum + y) % grain.components[0].height)
                cast(bytearray, grain.data)[
                    grain.components[0].offset + line_no*grain.components[0].stride:
                    grain.components[0].offset + line_no*grain.components[0].stride + grain.components[0].width*_bpp] = (
                        self._bar[0][y*grain.components[0].width * _bpp: (y+1)*grain.components[0].width * _bpp])
            for y in range(0, self._bar_height >> v_shift):
                line_no = (((fnum >> v_shift) + y) % grain.components[1].height)
                cast(bytearray, grain.data)[
                    grain.components[1].offset + line_no*grain.components[1].stride:
                    grain.components[1].offset + line_no*grain.components[1].stride + grain.components[1].width*_bpp] = (
                        self._bar[1][y*grain.components[1].width * _bpp: (y+1)*grain.components[1].width * _bpp])

                line_no = (((fnum >> v_shift) + y) % grain.components[2].height)
                cast(bytearray, grain.data)[
                    grain.components[2].offset + line_no*grain.components[2].stride:
                    grain.components[2].offset + line_no*grain.components[2].stride + grain.components[2].width*_bpp] = (
                        self._bar[2][y*grain.components[2].width * _bpp: (y+1)*grain.components[2].width * _bpp])

        return grain
