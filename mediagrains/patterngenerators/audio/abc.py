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

from ...cogenums import CogAudioFormat
from ...grain import AUDIOGRAIN
from ..abc import FixedRatePatternGenerator


__all__ = ["AudioPatternGenerator"]


class AudioPatternGenerator (FixedRatePatternGenerator[AUDIOGRAIN]):
    def __init__(
        self,
        src_id: UUID,
        flow_id: UUID,
        samples: int = 1920,
        channels: int = 1,
        cog_audio_format: CogAudioFormat = CogAudioFormat.S16_INTERLEAVED,
        sample_rate: int = 48000
    ):
        rate = Fraction(sample_rate, samples)
        super().__init__(rate)
        self._src_id = src_id
        self._flow_id = flow_id
        self._samples = samples
        self._channels = channels
        self._cog_audio_format = cog_audio_format
        self._sample_rate = sample_rate

    @property
    def src_id(self) -> UUID:
        return self._src_id

    @property
    def flow_id(self) -> UUID:
        return self._flow_id

    @property
    def samples(self) -> int:
        return self._samples

    @property
    def channels(self) -> int:
        return self._channels

    @property
    def cog_audio_format(self) -> CogAudioFormat:
        return self._cog_audio_format

    @property
    def sample_rate(self) -> int:
        return self._sample_rate
