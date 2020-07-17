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
from uuid import UUID

from ...cogenums import CogFrameFormat
from ...grain import VIDEOGRAIN
from ..abc import FixedRatePatternGenerator


__all__ = ["VideoPatternGenerator"]


class VideoPatternGenerator (FixedRatePatternGenerator[VIDEOGRAIN]):
    def __init__(self, src_id, flow_id, width, height,
                 rate=Fraction(25, 1),
                 cog_frame_format=CogFrameFormat.U8_444):
        super().__init__(rate)
        self._src_id = src_id
        self._flow_id = flow_id
        self._width = width
        self._height = height
        self._cog_frame_format = cog_frame_format

    @property
    def src_id(self) -> UUID:
        return self._src_id

    @property
    def flow_id(self) -> UUID:
        return self._flow_id

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def cog_frame_format(self) -> CogFrameFormat:
        return self._cog_frame_format
