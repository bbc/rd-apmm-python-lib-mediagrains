from typing import Optional, Awaitable, cast, Generator, Any, List
from ...typing import AudioGrainMetadataDict, GrainDataType, GrainDataParameterType
from inspect import isawaitable

from copy import copy, deepcopy
from uuid import UUID
from fractions import Fraction

import numpy as np
from numpy.lib.stride_tricks import as_strided

from mediatimestamp.immutable import SupportsMediaTimestamp
import mediagrains.grains as bytesgrain

from ...cogenums import (
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


def _channel_arrays_for_data_and_type(data: Optional[np.ndarray],
                                      format: CogAudioFormat,
                                      samples: int,
                                      channels: int) -> List[np.ndarray]:
    """This method returns a list of numpy array views which can be used to directly access the channels of the audio frame
    without any need for conversion or copying. This is not possible for all formats.

    24-bit samples are widened to 32-bit. Planar 24-bit samples held in the lower part of 32-bit are shifted to the
    upper part.
    """
    if data is None:
        return []
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


class AudioGrain (bytesgrain.AudioGrain):
    def __init__(self,
                 *args,
                 grain: bytesgrain.AudioGrain = None,
                 meta: AudioGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
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
                 flow_id: Optional[UUID] = None):
        if grain and isinstance(grain, bytesgrain.AudioGrain):
            meta = grain.meta
            data = grain.data
            super().__init__(meta=meta, data=data)
        else:
            if args and len(args) == 2:
                meta = cast(AudioGrainMetadataDict, args[0])
                data = cast(GrainDataParameterType, args[1])
            super().__init__(meta=meta, data=data, origin_timestamp=origin_timestamp,
                             creation_timestamp=creation_timestamp, sync_timestamp=sync_timestamp, rate=rate,
                             duration=duration, cog_audio_format=cog_audio_format, src_id=src_id, flow_id=flow_id,
                             samples=samples, channels=channels, sample_rate=sample_rate)
        self._data: Optional[np.ndarray]
        self._data_fetcher_coroutine: Optional[Awaitable[GrainDataType]]
        self.channel_data: List[np.ndarray]

        if self._data is not None:
            self._data = np.frombuffer(self._data, dtype=_dtype_from_cogaudioformat(self.format))
        if self._data is not None:
            self.channel_data = _channel_arrays_for_data_and_type(
                self._data, self.format, self.samples, self.channels
            )
        else:
            self.channel_data = []

    @property
    def length(self) -> int:
        if self._data is not None:
            return self._data.nbytes
        else:
            return 0

    @length.setter
    def length(self, L: int) -> None:
        # Get the length Property from the parent class and set the new value L
        super(AudioGrain, type(self)).length.fset(self, L)  # type: ignore

    @property
    def data(self) -> Optional[np.ndarray]:
        return self._data

    @data.setter
    def data(self, value: GrainDataParameterType):
        if isawaitable(value):
            self._data_fetcher_coroutine = cast(Awaitable[GrainDataType], value)
            self._data = None
            self.channel_data = []
        else:
            self._data_fetcher_coroutine = None
            self._data = np.frombuffer(cast(bytes, value), dtype=_dtype_from_cogaudioformat(self.format))
            self.channel_data = _channel_arrays_for_data_and_type(
                self._data, self.format, self.samples, self.channels
            )

    def __array__(self) -> Optional[np.ndarray]:
        return np.array(self.data)

    def __bytes__(self) -> bytes:
        if self._data is None:
            return bytes()
        return bytes(self._data)

    def __copy__(self) -> "AudioGrain":
        return AudioGrain(meta=copy(self.meta), data=self.data)

    def __deepcopy__(self, memo) -> "AudioGrain":
        return AudioGrain(meta=deepcopy(self.meta),
                          data=self._data.copy() if self._data is not None else None)

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

    async def __aenter__(self) -> "AudioGrain":
        await self
        return self

    async def __aexit__(self, *args, **kwargs):
        pass
