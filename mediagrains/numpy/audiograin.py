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

from typing import Optional, Awaitable, cast, overload, Generator, Any, List
from ..typing import AudioGrainMetadataDict, GrainDataType, GrainDataParameterType
from inspect import isawaitable

from copy import copy, deepcopy
from uuid import UUID
from fractions import Fraction

import numpy as np
from numpy.lib.stride_tricks import as_strided

from mediatimestamp.immutable import SupportsMediaTimestamp
from mediagrains import grain as bytesgrain
from mediagrains import grain_constructors as bytesgrain_constructors

from ..cogenums import (
    CogAudioFormat,
    COG_AUDIO_IS_INT,
    COG_AUDIO_IS_FLOAT,
    COG_AUDIO_IS_DOUBLE,
    COG_AUDIO_FORMAT_SAMPLEBYTES,
    COG_AUDIO_IS_PLANES,
    COG_AUDIO_IS_INTERLEAVED,
    COG_AUDIO_IS_PAIRS,
    COG_AUDIO_FORMAT_DEPTH,
    COG_AUDIO_FORMAT_DEPTH_S24
)

__all__ = ['AudioGrain', 'AUDIOGRAIN']


def _dtype_from_cogaudioformat(format: CogAudioFormat) -> np.dtype:
    """This method returns the numpy "data type" for a particular audio format."""
    if COG_AUDIO_IS_INT(format):
        if COG_AUDIO_FORMAT_DEPTH(format) == COG_AUDIO_FORMAT_DEPTH_S24:
            return np.dtype(np.uint8)
        elif COG_AUDIO_FORMAT_SAMPLEBYTES(format) == 2:
            return np.dtype(np.int16)
        elif COG_AUDIO_FORMAT_SAMPLEBYTES(format) == 4:
            return np.dtype(np.int32)
        elif COG_AUDIO_FORMAT_SAMPLEBYTES(format) == 8:
            return np.dtype(np.int64)
    elif COG_AUDIO_IS_FLOAT(format):
        return np.dtype(np.float32)
    elif COG_AUDIO_IS_DOUBLE(format):
        return np.dtype(np.float64)

    raise NotImplementedError("Cog Audio Format not amongst those supported for numpy array interpretation")


def _channel_arrays_for_data_and_type(data: np.ndarray,
                                      format: CogAudioFormat,
                                      samples: int,
                                      channels: int) -> List[np.ndarray]:
    """This method returns a list of numpy array views which can be used to directly access the channels of the audio frame
    without any need for conversion or copying. This is not possible for all formats.

    24-bit samples are widened to 32-bit. Planar 24-bit samples held in the lower part of 32-bit are shifted to the
    upper part.
    """
    if COG_AUDIO_IS_INT(format) and COG_AUDIO_FORMAT_DEPTH(format) == COG_AUDIO_FORMAT_DEPTH_S24:
        if COG_AUDIO_FORMAT_SAMPLEBYTES(format) == 3:
            # Widen samples to int32
            wide_data = np.zeros((len(data) // 3, 4), dtype=np.uint8)
            wide_data[:, 1:] = data.reshape((-1, 3))
            data = wide_data.view(np.int32)
        else:
            # The 24 bits are stored in the least significant bits. Shift to the most
            # significant bits end to produce int32 samples
            data = data.view(np.int32)
            data <<= 8
        sample_bytes = 4
    else:
        sample_bytes = COG_AUDIO_FORMAT_SAMPLEBYTES(format)

    channel_data: List[np.ndarray] = []
    if COG_AUDIO_IS_PLANES(format):
        for channel in range(channels):
            plane_offset = channel * samples
            next_plane_offset = (channel + 1) * samples
            channel_data.append(
                data[plane_offset:next_plane_offset]
            )
    elif COG_AUDIO_IS_INTERLEAVED(format):
        for channel in range(channels):
            interleave_offset = channel
            next_interleave_offset = channel + samples
            channel_data.append(
                as_strided(
                    data[interleave_offset:next_interleave_offset],
                    shape=(samples,),
                    strides=(sample_bytes * channels,)
                )
            )
    elif COG_AUDIO_IS_PAIRS(format):
        for channel in range(channels):
            channel_pair = channel // 2
            pair_offset = 2 * channel_pair * samples
            next_pair_offset = 2 * (channel_pair + 1) * samples
            channel_data.append(
                as_strided(
                    data[pair_offset+(channel % 2):next_pair_offset],
                    shape=(samples,),
                    strides=(sample_bytes * 2,)
                )
            )

    return channel_data


class AUDIOGRAIN (bytesgrain.AUDIOGRAIN):
    def __init__(self, meta: AudioGrainMetadataDict, data: GrainDataParameterType):
        super().__init__(meta, data)
        self._data: np.ndarray
        self._data_fetcher_coroutine: Optional[Awaitable[GrainDataType]]
        self.channel_data: List[np.ndarray]

        if self._data is not None:
            self._data = np.frombuffer(self._data, dtype=_dtype_from_cogaudioformat(self.format))
            self.channel_data = _channel_arrays_for_data_and_type(
                self._data, self.format, self.samples, self.channels
            )
        else:
            self.channel_data = []

    @property
    def length(self) -> int:
        return self._data.nbytes

    @length.setter
    def length(self, L: int) -> None:
        # Get the length Property from the parent class and set the new value L
        super(AUDIOGRAIN, type(self)).length.fset(self, L)  # type: ignore

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value: GrainDataParameterType):
        if isawaitable(value):
            self._data_fetcher_coroutine = cast(Awaitable[GrainDataType], value)
            self._data = None
            self.channel_data = []
        else:
            self._data_fetcher_coroutine = None
            self._data = np.frombuffer(cast(GrainDataType, value), dtype=_dtype_from_cogaudioformat(self.format))
            self.channel_data = _channel_arrays_for_data_and_type(
                self._data, self.format, self.samples, self.channels
            )

    def __array__(self) -> np.ndarray:
        return np.array(self.data)

    def __bytes__(self) -> bytes:
        return bytes(self._data)

    def __copy__(self) -> "AUDIOGRAIN":
        return AudioGrain(copy(self.meta), self.data)

    def __deepcopy__(self, memo) -> "AUDIOGRAIN":
        return AudioGrain(deepcopy(self.meta), self._data.copy())

    def __repr__(self) -> str:
        if self.data is None:
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< numpy data of length {} >)".format(self._factory, self.meta, len(self.data))

    def __await__(self) -> Generator[Any, None, np.ndarray]:
        async def __inner():
            if self._data is None and self._data_fetcher_coroutine is not None:
                self.data = await self._data_fetcher_coroutine
            return self.data
        return __inner().__await__()

    async def __aenter__(self) -> "AUDIOGRAIN":
        await self
        return self

    async def __aexit__(self, *args, **kwargs):
        pass


@overload
def AudioGrain(grain: bytesgrain.AUDIOGRAIN) -> AUDIOGRAIN: ...


@overload
def AudioGrain(src_id_or_meta: AudioGrainMetadataDict,
               flow_id_or_data: GrainDataParameterType = None) -> AUDIOGRAIN: ...


@overload
def AudioGrain(src_id_or_meta: Optional[UUID] = None,
               flow_id_or_data: Optional[UUID] = None,
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
               data: GrainDataParameterType = None) -> AUDIOGRAIN: ...


def AudioGrain(*args, **kwargs):
    """If the first argument is a mediagrains.AUDIOGRAIN then return a mediagrains.numpy.AUDIOGRAIN representing the same data.

    Otherwise takes the same parameters as mediagrains.AudioGrain and returns the same grain converted into a mediagrains.numpy.AUDIOGRAIN
    """
    if len(args) == 1 and isinstance(args[0], bytesgrain.AUDIOGRAIN):
        rawgrain = args[0]
    else:
        rawgrain = bytesgrain_constructors.AudioGrain(*args, **kwargs)

    if rawgrain.data is not None:
        return AUDIOGRAIN(rawgrain.meta, rawgrain.data)
    else:
        return AUDIOGRAIN(rawgrain.meta, rawgrain._data_fetcher_coroutine)
