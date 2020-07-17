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

from typing import Optional
from copy import deepcopy

from mediatimestamp import TimeValue

from ...grain import VIDEOGRAIN
from .abc import VideoPatternGenerator


__all__ = ["StillPatternGenerator"]


class StillPatternGenerator (VideoPatternGenerator):
    def __init__(self, template_grain: VIDEOGRAIN):
        super().__init__(
            src_id=template_grain.source_id,
            flow_id=template_grain.flow_id,
            width=template_grain.width,
            height=template_grain.height,
            rate=template_grain.rate,
            cog_frame_format=template_grain.format)
        self._template_grain = template_grain

    def get(self, key: TimeValue, default: Optional[VIDEOGRAIN] = None) -> Optional[VIDEOGRAIN]:
        tv = TimeValue(key, rate=self.rate)

        if tv == key:
            grain = deepcopy(self._template_grain)
            grain.origin_timestamp = key.as_timestamp()
            grain.sync_timestamp = grain.origin_timestamp
            return grain
        else:
            return default
