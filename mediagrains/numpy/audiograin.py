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

"""\
Library for handling audio mediagrains in numpy arrays
"""

from typing import Optional, TypeAlias, cast
from ..typing import AudioGrainMetadataDict, GrainDataParameterType
from uuid import UUID
from fractions import Fraction

from mediatimestamp.immutable import SupportsMediaTimestamp
from .numpy_grains import AudioGrain as npAudioGrain
from mediagrains.grains import AudioGrain as byAudioGrain

from ..cogenums import (
    CogAudioFormat
)
from deprecated import deprecated

__all__ = ['AudioGrain', 'AUDIOGRAIN']


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.numpy.numpy_grains`.')
def AudioGrain(*args,
               origin_timestamp: Optional[SupportsMediaTimestamp] = None,
               sync_timestamp: Optional[SupportsMediaTimestamp] = None,
               creation_timestamp: Optional[SupportsMediaTimestamp] = None,
               rate: Fraction = Fraction(25, 1),
               duration: Fraction = Fraction(1, 25),
               cog_audio_format: CogAudioFormat = CogAudioFormat.INVALID,
               samples: int = 0,
               channels: int = 0,
               sample_rate: int = 48000,
               src_id: Optional[UUID] = None,
               source_id: Optional[UUID] = None,
               format: Optional[CogAudioFormat] = None,
               flow_id: Optional[UUID] = None,
               data: GrainDataParameterType = None,
               meta: AudioGrainMetadataDict = None):
    """If the first argument is a mediagrains.AUDIOGRAIN then return a mediagrains.numpy.AUDIOGRAIN representing the
    same data.

    Otherwise takes the same parameters as mediagrains.AudioGrain and returns the same grain converted into a
    mediagrains.numpy.AUDIOGRAIN
    """
    if args and isinstance(args[0], byAudioGrain):
        return npAudioGrain(grain=args[0])

    if format:
        cog_audio_format = format
    if source_id:
        src_id = source_id

    if args:
        if isinstance(args[0], dict):
            meta = cast(AudioGrainMetadataDict, args[0])
        else:
            src_id = args[0]
        if isinstance(args[1], UUID):
            flow_id = args[1]
        else:
            data = args[1]

    return npAudioGrain(origin_timestamp=origin_timestamp,
                        creation_timestamp=creation_timestamp,
                        sync_timestamp=sync_timestamp,
                        rate=rate,
                        duration=duration,
                        cog_audio_format=cog_audio_format,
                        samples=samples,
                        channels=channels,
                        sample_rate=sample_rate,
                        src_id=src_id,
                        flow_id=flow_id,
                        data=data,
                        meta=meta)


AUDIOGRAIN: TypeAlias = npAudioGrain
