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
from uuid import UUID
from math import sin, pi
from typing import Optional, Dict, List, Union
import struct
from fractions import Fraction

from mediatimestamp import TimeValue

from .abc import AudioPatternGenerator
from ...grain import AUDIOGRAIN
from ...grain_constructors import AudioGrain
from ...cogenums import CogAudioFormat


__all__ = ["Tone", "Tone1K", "Silence"]


class Tone(AudioPatternGenerator):
    def __init__(
        self,
        src_id: UUID,
        flow_id: UUID,
        samples: int = 1920,
        channels: int = 1,
        cog_audio_format: CogAudioFormat = CogAudioFormat.S16_INTERLEAVED,
        sample_rate: int = 48000,
        frequency: int = 1000,
        volume: float = 0.5
    ):
        super().__init__(
            src_id=src_id,
            flow_id=flow_id,
            samples=samples,
            channels=channels,
            cog_audio_format=cog_audio_format,
            sample_rate=sample_rate
        )

        self.volume = volume
        self.frequency = int(frequency)
        if self.frequency == 0:
            self.looplen = 1
        else:
            self.looplen = self.sample_rate
            if (self.looplen % self.frequency) == 0:
                self.looplen //= self.frequency
        self._sample_values = [sin(2.0*n*pi*float(self.frequency)/float(self.sample_rate)) for n in range(0, self.looplen)]

        self.data_samples: Dict[int, bytes] = {}

        if cog_audio_format not in [
            CogAudioFormat.S16_PLANES,
            CogAudioFormat.S16_PAIRS,
            CogAudioFormat.S16_INTERLEAVED,
            CogAudioFormat.S24_PLANES,
            CogAudioFormat.S24_PAIRS,
            CogAudioFormat.S24_INTERLEAVED,
            CogAudioFormat.S32_PLANES,
            CogAudioFormat.S32_PAIRS,
            CogAudioFormat.S32_INTERLEAVED,
            CogAudioFormat.FLOAT_PLANES,
            CogAudioFormat.FLOAT_PAIRS,
            CogAudioFormat.FLOAT_INTERLEAVED,
            CogAudioFormat.DOUBLE_PLANES,
            CogAudioFormat.DOUBLE_PAIRS,
            CogAudioFormat.DOUBLE_INTERLEAVED,
        ]:
            raise ValueError("Unsupported cog audio format")

    def _get_samples(self, offs: int) -> bytes:
        if offs not in self.data_samples:
            formatted_sample_data: List[float]
            depth: Union[int, str]

            if self.cog_audio_format in [CogAudioFormat.S16_PLANES,
                                         CogAudioFormat.S16_PAIRS,
                                         CogAudioFormat.S16_INTERLEAVED]:
                formatted_sample_data = [round(x*self.volume*(1 << 15)) for x in self._sample_values]
                depth = 16
            elif self.cog_audio_format in [CogAudioFormat.S24_PLANES,
                                           CogAudioFormat.S24_PAIRS,
                                           CogAudioFormat.S24_INTERLEAVED]:
                formatted_sample_data = [round(x*self.volume*(1 << 23)) for x in self._sample_values]
                depth = 24
            elif self.cog_audio_format in [CogAudioFormat.S32_PLANES,
                                           CogAudioFormat.S32_PAIRS,
                                           CogAudioFormat.S32_INTERLEAVED]:
                formatted_sample_data = [round(x*self.volume*(1 << 31)) for x in self._sample_values]
                depth = 32
            elif self.cog_audio_format in [CogAudioFormat.FLOAT_PLANES,
                                           CogAudioFormat.FLOAT_PAIRS,
                                           CogAudioFormat.FLOAT_INTERLEAVED]:
                formatted_sample_data = [x*self.volume for x in self._sample_values]
                depth = 'f'
            elif self.cog_audio_format in [CogAudioFormat.DOUBLE_PLANES,
                                           CogAudioFormat.DOUBLE_PAIRS,
                                           CogAudioFormat.DOUBLE_INTERLEAVED]:
                formatted_sample_data = [x*self.volume for x in self._sample_values]
                depth = 'd'

            planes = False
            pairs = False
            interleaved = False

            if self.cog_audio_format in [CogAudioFormat.S16_PLANES,
                                         CogAudioFormat.S24_PLANES,
                                         CogAudioFormat.S32_PLANES,
                                         CogAudioFormat.FLOAT_PLANES,
                                         CogAudioFormat.DOUBLE_PLANES]:
                planes = True
            elif self.cog_audio_format in [CogAudioFormat.S16_PAIRS,
                                           CogAudioFormat.S24_PAIRS,
                                           CogAudioFormat.S32_PAIRS,
                                           CogAudioFormat.FLOAT_PAIRS,
                                           CogAudioFormat.DOUBLE_PAIRS]:
                pairs = True
            elif self.cog_audio_format in [CogAudioFormat.S16_INTERLEAVED,
                                           CogAudioFormat.S24_INTERLEAVED,
                                           CogAudioFormat.S32_INTERLEAVED,
                                           CogAudioFormat.FLOAT_INTERLEAVED,
                                           CogAudioFormat.DOUBLE_INTERLEAVED]:
                interleaved = True

            line = [formatted_sample_data[n % len(formatted_sample_data)] for n in range(offs, offs + self.samples)]
            if planes:
                line = line * self.channels
            elif pairs:
                line = [x for x in line for _ in range(0, 2)] * (self.channels//2)
            elif interleaved:
                line = [x for x in line for _ in range(0, self.channels)]

            if depth == 16:
                self.data_samples[offs] = struct.pack('@' + ('h'*self.samples*self.channels), *line)
            elif depth == 24:
                self.data_samples[offs] = b''.join(struct.pack('@i', x)[:3] for x in line)
            elif depth == 32:
                self.data_samples[offs] = struct.pack('@' + ('i'*self.samples*self.channels), *line)
            elif depth == 'f':
                self.data_samples[offs] = struct.pack('@' + ('f'*self.samples*self.channels), *line)
            elif depth == 'd':
                self.data_samples[offs] = struct.pack('@' + ('d'*self.samples*self.channels), *line)

        return self.data_samples[offs]

    def get(self, key: TimeValue, default: Optional[AUDIOGRAIN] = None) -> Optional[AUDIOGRAIN]:
        tv = TimeValue(key, rate=Fraction(self.sample_rate))
        sample_count = tv.as_count()

        if sample_count % self.samples != 0:
            return None

        offs = sample_count % self.looplen

        ag = AudioGrain(
            self.src_id,
            self.flow_id,
            origin_timestamp=tv.as_timestamp(),
            cog_audio_format=self.cog_audio_format,
            samples=self.samples,
            channels=self.channels,
            rate=self.rate,
            sample_rate=self.sample_rate)

        ag.data = bytearray(self._get_samples(offs)[:ag.expected_length])

        return ag


def Tone1K(
    src_id: UUID,
    flow_id: UUID,
    samples: int = 1920,
    channels: int = 1,
    cog_audio_format: CogAudioFormat = CogAudioFormat.S16_INTERLEAVED,
    sample_rate: int = 48000,
    volume: float = 0.5
):
    return Tone(
        src_id=src_id,
        flow_id=flow_id,
        samples=samples,
        channels=channels,
        cog_audio_format=cog_audio_format,
        sample_rate=sample_rate,
        volume=volume,
        frequency=1000
    )


def Silence(
    src_id: UUID,
    flow_id: UUID,
    samples: int = 1920,
    channels: int = 1,
    cog_audio_format: CogAudioFormat = CogAudioFormat.S16_INTERLEAVED,
    sample_rate: int = 48000
):
    return Tone(
        src_id=src_id,
        flow_id=flow_id,
        samples=samples,
        channels=channels,
        cog_audio_format=cog_audio_format,
        sample_rate=sample_rate,
        volume=0.0,
        frequency=0
    )
