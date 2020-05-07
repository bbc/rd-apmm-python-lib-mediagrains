#
# Copyright 2018 British Broadcasting Corporation
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
The submodule of mediagrains which contains the functions used to construct
grains.
"""

from uuid import UUID
from mediatimestamp.immutable import Timestamp, SupportsMediaTimestamp, mediatimestamp
from fractions import Fraction

from typing import Optional, cast, Sized, List, overload
from .typing import (
    GrainDataParameterType,
    GrainMetadataDict,
    EmptyGrainMetadataDict,
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    VideoGrainMetadataDict,
    EventGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    VideoGrainComponentDict)

from .cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat
from .grain import GRAIN, VIDEOGRAIN, AUDIOGRAIN, CODEDVIDEOGRAIN, CODEDAUDIOGRAIN, EVENTGRAIN, size_for_audio_format


__all__ = ["Grain", "VideoGrain", "AudioGrain", "CodedVideoGrain", "CodedAudioGrain", "EventGrain"]


@overload
def Grain(src_id_or_meta: GrainMetadataDict,
          flow_id_or_data: GrainDataParameterType = None) -> GRAIN: ...


@overload
def Grain(src_id_or_meta: Optional[UUID] = None,
          flow_id_or_data: Optional[UUID] = None,
          origin_timestamp: Optional[SupportsMediaTimestamp] = None,
          sync_timestamp: Optional[SupportsMediaTimestamp] = None,
          creation_timestamp: Optional[SupportsMediaTimestamp] = None,
          rate: Fraction = Fraction(0, 1),
          duration: Fraction = Fraction(0, 1),
          flow_id: Optional[UUID] = None,
          data: GrainDataParameterType = None,
          src_id: Optional[UUID] = None,
          source_id: Optional[UUID] = None,
          meta: Optional[GrainMetadataDict] = None) -> GRAIN: ...


def Grain(src_id_or_meta=None,
          flow_id_or_data=None,
          origin_timestamp=None,
          sync_timestamp=None,
          creation_timestamp=None,
          rate=Fraction(0, 1),
          duration=Fraction(0, 1),
          flow_id=None,
          data=None,
          src_id=None,
          source_id=None,
          meta=None):
    """\
Function called to construct a grain either from existing data or with new data.

First method of calling:

    Grain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload. If the meta dictionary contains a key
"grain" identifying a dictionary containing the key "grain_type" and this key is
one of the values: "video", "audio", "coded_video", "coded_audio" or "event" then
the parameters will be passed through to the relevent specialised constructor
function, otherwise a generic grain object will be returned which wraps the meta
and data elements.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for a Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "empty",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                }
            }
        }

Alternatively it may be called as:

    Grain(src_id, flow_id, origin_timestamp=None,
          sync_timestamp=None, rate=Fraction(25, 1), duration=Fraction(1, 25))

in which case a new grain will be constructed with type "empty" and data set to
None. The new grain's creation_timestamp will be set to the current time. If no
origin_timestamp is provided then it will be set to the creation_timestamp. If
no sync_timestamp is provided then it will be set to the origin_timestamp.



In either case the value returned by this function will be an instance of the
class mediagrains.grain.GRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    if source_id is not None:
        src_id = source_id

    if meta is None:
        if isinstance(src_id_or_meta, dict):
            meta = src_id_or_meta
            if data is None and not isinstance(flow_id_or_data, UUID):
                data = flow_id_or_data
        else:
            if src_id is None and isinstance(src_id_or_meta, UUID):
                src_id = src_id_or_meta
            if flow_id is None and isinstance(flow_id_or_data, UUID):
                flow_id = flow_id_or_data

    if meta is None:
        if creation_timestamp is None:
            cts = Timestamp.get_time()
        else:
            cts = creation_timestamp
        ots = origin_timestamp
        sts = sync_timestamp

        if ots is None:
            ots = cts
        if sts is None:
            sts = ots

        if src_id is None or flow_id is None:
            raise AttributeError("Must specify at least meta or src_id and flow_id")

        if not isinstance(src_id, UUID) or not isinstance(flow_id, UUID):
            raise AttributeError("Invalid types for src_id and flow_id")

        meta = EmptyGrainMetadataDict({
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                'grain_type': "empty",
                'source_id': str(src_id),
                'flow_id': str(flow_id),
                'origin_timestamp': str(mediatimestamp(ots)),
                'sync_timestamp': str(mediatimestamp(sts)),
                'creation_timestamp': str(mediatimestamp(cts)),
                'rate': {
                    'numerator': Fraction(rate).numerator,
                    'denominator': Fraction(rate).denominator
                },
                'duration': {
                    'numerator': Fraction(duration).numerator,
                    'denominator': Fraction(duration).denominator
                }
            }
        })
        data = None

    if 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'video':
        return VideoGrain(cast(VideoGrainMetadataDict, meta), data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'audio':
        return AudioGrain(cast(AudioGrainMetadataDict, meta), data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'coded_video':
        return CodedVideoGrain(cast(CodedVideoGrainMetadataDict, meta), data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] == 'coded_audio':
        return CodedAudioGrain(cast(CodedAudioGrainMetadataDict, meta), data)
    elif 'grain' in meta and 'grain_type' in meta['grain'] and meta['grain']['grain_type'] in ['event', 'data']:
        return EventGrain(cast(EventGrainMetadataDict, meta), data)
    else:
        return GRAIN(meta, data)


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


def AudioGrain(src_id_or_meta=None,
               flow_id_or_data=None,
               origin_timestamp=None,
               sync_timestamp=None,
               creation_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               cog_audio_format=CogAudioFormat.INVALID,
               samples=0,
               channels=0,
               sample_rate=48000,
               src_id=None,
               source_id=None,
               format=None,
               flow_id=None,
               data=None):
    """\
Function called to construct an audio grain either from existing data or with new data.

First method of calling:

    AudioGrain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for an Audio Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "cog_audio": {
                    "format": cog_audio_format, # int or CogAudioFormat
                    "samples": samples, # int
                    "channels": channels, # int
                    "sample_rate": sample_rate # int
                }
            }
        }

Alternatively it may be called as:

    AudioGrain(src_id, flow_id,
               origin_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               cog_audio_format=CogAudioFormat.INVALID,
               samples=0,
               channels=0,
               sample_rate=48000,
               data=None)

in which case a new grain will be constructed with type "audio" and the
specified metadata. If the data argument is None then a new bytearray object
will be constructed with size determined by the samples, channels, and format
specified.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.AUDIOGRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    meta: Optional[AudioGrainMetadataDict] = None

    if cog_audio_format is None:
        cog_audio_format = format
    if source_id is not None:
        src_id = source_id

    if isinstance(src_id_or_meta, dict):
        meta = cast(AudioGrainMetadataDict, src_id_or_meta)
        if data is None and not isinstance(flow_id_or_data, UUID):
            data = flow_id_or_data
    else:
        if src_id is None and isinstance(src_id_or_meta, UUID):
            src_id = src_id_or_meta
        if flow_id is None and isinstance(flow_id_or_data, UUID):
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = creation_timestamp
        if cts is None:
            cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                'grain_type': "audio",
                'source_id': str(src_id),
                'flow_id': str(flow_id),
                'origin_timestamp': str(mediatimestamp(origin_timestamp)),
                'sync_timestamp': str(mediatimestamp(sync_timestamp)),
                'creation_timestamp': str(mediatimestamp(cts)),
                'rate': {
                    'numerator': Fraction(rate).numerator,
                    'denominator': Fraction(rate).denominator
                },
                'duration': {
                    'numerator': Fraction(duration).numerator,
                    'denominator': Fraction(duration).denominator
                },
                'cog_audio': {
                    "format": cog_audio_format,
                    "samples": samples,
                    "channels": channels,
                    "sample_rate": sample_rate
                }
            }
        }

    if data is None:
        size = size_for_audio_format(cog_audio_format, channels, samples)
        data = bytearray(size)

    return AUDIOGRAIN(meta, data)


@overload
def CodedAudioGrain(src_id_or_meta: CodedAudioGrainMetadataDict,
                    flow_id_or_data: GrainDataParameterType = None) -> CODEDAUDIOGRAIN: ...


@overload
def CodedAudioGrain(src_id_or_meta: Optional[UUID] = None,
                    flow_id_or_data: Optional[UUID] = None,
                    origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                    creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                    sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                    rate: Fraction = Fraction(25, 1),
                    duration: Fraction = Fraction(1, 25),
                    cog_audio_format: CogAudioFormat = CogAudioFormat.INVALID,
                    samples: int = 0,
                    channels: int = 0,
                    priming: int = 0,
                    remainder: int = 0,
                    sample_rate: int = 48000,
                    length: Optional[int] = None,
                    src_id: Optional[UUID] = None,
                    source_id: Optional[UUID] = None,
                    format: Optional[CogAudioFormat] = None,
                    flow_id: Optional[UUID] = None,
                    data: GrainDataParameterType = None) -> CODEDAUDIOGRAIN: ...


def CodedAudioGrain(src_id_or_meta=None,
                    flow_id_or_data=None,
                    origin_timestamp=None,
                    creation_timestamp=None,
                    sync_timestamp=None,
                    rate=Fraction(25, 1),
                    duration=Fraction(1, 25),
                    cog_audio_format=CogAudioFormat.INVALID,
                    samples=0,
                    channels=0,
                    priming=0,
                    remainder=0,
                    sample_rate=48000,
                    length=None,
                    src_id=None,
                    source_id=None,
                    format=None,
                    flow_id=None,
                    data=None):
    """\
Function called to construct a coded audio grain either from existing data or with new data.

First method of calling:

    CodedAudioGrain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for a Coded Audio Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_audio",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "cog_coded_audio": {
                    "format": cog_audio_format, # int or CogAudioFormat
                    "samples": samples, # int
                    "channels": channels, # int
                    "priming": priming, # int
                    "remainder": remainder, # int
                    "sample_rate": sample_rate # int
                }
            }
        }

Alternatively it may be called as:

    CodedAudioGrain(src_id, flow_id,
                    origin_timestamp=None,
                    sync_timestamp=None,
                    rate=Fraction(25, 1),
                    duration=Fraction(1, 25),
                    samples=0,
                    channels=0,
                    priming=0,
                    remainder=0,
                    sample_rate=48000,
                    length=None,
                    data=None)

in which case a new grain will be constructed with type "coded_audio" and the
specified metadata. If the data argument is None and the length argument is an
integer then a new bytearray object will be constructed with size equal to the
length argument.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.CODEDAUDIOGRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""

    meta: Optional[CodedAudioGrainMetadataDict] = None

    if source_id is not None:
        src_id = source_id

    if cog_audio_format is None:
        cog_audio_format = format

    if isinstance(src_id_or_meta, dict):
        meta = cast(CodedAudioGrainMetadataDict, src_id_or_meta)
        if data is None and not isinstance(flow_id_or_data, UUID):
            data = flow_id_or_data
    else:
        if src_id is None and isinstance(src_id_or_meta, UUID):
            src_id = src_id_or_meta
        if flow_id is None and isinstance(flow_id_or_data, UUID):
            flow_id = flow_id_or_data

    if length is None:
        if data is not None and hasattr(data, "__len__"):
            length = len(cast(Sized, data))
        else:
            length = 0

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                'grain_type': "coded_audio",
                'source_id': str(src_id),
                'flow_id': str(flow_id),
                'origin_timestamp': str(mediatimestamp(origin_timestamp)),
                'sync_timestamp': str(mediatimestamp(sync_timestamp)),
                'creation_timestamp': str(mediatimestamp(cts)),
                'rate': {
                    'numerator': Fraction(rate).numerator,
                    'denominator': Fraction(rate).denominator
                },
                'duration': {
                    'numerator': Fraction(duration).numerator,
                    'denominator': Fraction(duration).denominator
                },
                'cog_coded_audio': {
                    "format": cog_audio_format,
                    "samples": samples,
                    "channels": channels,
                    "priming": priming,
                    "remainder": remainder,
                    "sample_rate": sample_rate
                }
            }
        }

    if data is None:
        data = bytearray(length)

    return CODEDAUDIOGRAIN(meta, data)


@overload
def VideoGrain(src_id_or_meta: VideoGrainMetadataDict,
               flow_id_or_data: GrainDataParameterType = None) -> VIDEOGRAIN: ...


@overload
def VideoGrain(src_id_or_meta: Optional[UUID] = None,
               flow_id_or_data: Optional[UUID] = None,
               origin_timestamp: Optional[SupportsMediaTimestamp] = None,
               creation_timestamp: Optional[SupportsMediaTimestamp] = None,
               sync_timestamp: Optional[SupportsMediaTimestamp] = None,
               rate: Fraction = Fraction(25, 1),
               duration: Fraction = Fraction(1, 25),
               cog_frame_format: CogFrameFormat = CogFrameFormat.UNKNOWN,
               width: int = 1920,
               height: int = 1080,
               cog_frame_layout: CogFrameLayout = CogFrameLayout.UNKNOWN,
               src_id: Optional[UUID] = None,
               source_id: Optional[UUID] = None,
               format: Optional[CogFrameFormat] = None,
               layout: Optional[CogFrameLayout] = None,
               flow_id: Optional[UUID] = None,
               data: GrainDataParameterType = None) -> VIDEOGRAIN: ...


def VideoGrain(src_id_or_meta=None,
               flow_id_or_data=None,
               origin_timestamp=None,
               creation_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               cog_frame_format=CogFrameFormat.UNKNOWN,
               width=1920,
               height=1080,
               cog_frame_layout=CogFrameLayout.UNKNOWN,
               src_id=None,
               source_id=None,
               format=None,
               layout=None,
               flow_id=None,
               data=None):
    """\
Function called to construct a video grain either from existing data or with new data.

First method of calling:

    VideoGrain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for a Video Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "cog_frame": {
                    "format": cog_frame_format, # int or CogFrameFormat
                    "width": width, # int
                    "height": height, # int
                    "layout": cog_frame_layout, # int of CogFrameLayout
                    "extension": 0, # int
                    "components": [
                        {
                            "stride": luma_stride, # int
                            "width": luma_width, # int
                            "height": luma_height, # int
                            "length": luma_length # int
                        },
                        {
                            "stride": chroma_stride, # int
                            "width": chroma_width, # int
                            "height": chroma_height, # int
                            "length": chroma_length # int
                        },
                        {
                            "stride": chroma_stride, # int
                            "width": chroma_width, # int
                            "height": chroma_height, # int
                            "length": chroma_length # int
                        },
                    ]
                }
            }
        }

Alternatively it may be called as:

    VideoGrain(src_id, flow_id,
               origin_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               cog_frame_format=CogFrameFormat.UNKNOWN,
               width=1920,
               height=1080,
               cog_frame_layout=CogFrameLayout.UNKNOWN,
               data=None):

in which case a new grain will be constructed with type "video" and the
specified metadata. If the data argument is None then a new bytearray object
will be constructed with size determined by the format, height, and width.
The components array will similarly be filled out automatically with correct
data for the format and size specified.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.VIDEOGRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    meta: Optional[VideoGrainMetadataDict] = None

    if cog_frame_format is None:
        cog_frame_format = format
    if source_id is not None:
        src_id = source_id
    if cog_frame_layout is None:
        cog_frame_layout = layout

    if isinstance(src_id_or_meta, dict):
        meta = cast(VideoGrainMetadataDict, src_id_or_meta)
        if data is None and not isinstance(flow_id_or_data, UUID):
            data = flow_id_or_data
    else:
        if src_id is None and isinstance(src_id_or_meta, UUID):
            src_id = src_id_or_meta
        if flow_id is None and isinstance(flow_id_or_data, UUID):
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = creation_timestamp
        if cts is None:
            cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                'grain_type': "video",
                'source_id': str(src_id),
                'flow_id': str(flow_id),
                'origin_timestamp': str(mediatimestamp(origin_timestamp)),
                'sync_timestamp': str(mediatimestamp(sync_timestamp)),
                'creation_timestamp': str(mediatimestamp(cts)),
                'rate': {
                    'numerator': Fraction(rate).numerator,
                    'denominator': Fraction(rate).denominator,
                },
                'duration': {
                    'numerator': Fraction(duration).numerator,
                    'denominator': Fraction(duration).denominator,
                },
                'cog_frame': {
                    "format": cog_frame_format,
                    "width": width,
                    "height": height,
                    "layout": cog_frame_layout,
                    "extension": 0,
                    "components": []
                }
            },
        }

    def size_for_format(fmt: CogFrameFormat, w: int, h: int) -> int:
        if ((fmt >> 8) & 0x1) == 0x00:  # Cog frame is not packed
            h_shift = (fmt & 0x01)
            v_shift = ((fmt >> 1) & 0x01)
            depth = (fmt & 0xc)
            if depth == 0:
                bpv = 1
            elif depth == 4:
                bpv = 2
            else:
                bpv = 4

            return (w*h + 2*((w*h) >> (h_shift + v_shift)))*bpv
        else:
            if fmt in (CogFrameFormat.YUYV,
                       CogFrameFormat.UYVY,
                       CogFrameFormat.AYUV):
                return w*h*2
            elif fmt in (CogFrameFormat.RGBx,
                         CogFrameFormat.RGBA,
                         CogFrameFormat.xRGB,
                         CogFrameFormat.ARGB,
                         CogFrameFormat.BGRx,
                         CogFrameFormat.BGRA,
                         CogFrameFormat.xBGR,
                         CogFrameFormat.ABGR):
                return w*h*4
            elif fmt == CogFrameFormat.RGB:
                return w*h*3
            elif fmt == CogFrameFormat.v210:
                return h*(((w + 47) // 48) * 128)
            elif fmt == CogFrameFormat.v216:
                return w*h*4
            else:
                return 0

    if data is None:
        size = size_for_format(cog_frame_format, width, height)
        data = bytearray(size)

    def components_for_format(fmt: CogFrameFormat, w: int, h: int) -> List[VideoGrainComponentDict]:
        components: List[VideoGrainComponentDict] = []
        if ((fmt >> 8) & 0x1) == 0x00:  # Cog frame is not packed
            h_shift = (fmt & 0x01)
            v_shift = ((fmt >> 1) & 0x01)
            depth = (fmt & 0xc)
            if depth == 0:
                bpv = 1
            elif depth == 4:
                bpv = 2
            else:
                bpv = 4

            offset = 0
            components.append({
                'stride': w*bpv,
                'offset': offset,
                'width': w,
                'height': h,
                'length': w*h*bpv
            })
            offset += w*h*bpv

            components.append({
                'stride': (w >> h_shift)*bpv,
                'offset': offset,
                'width': w >> h_shift,
                'height': h >> v_shift,
                'length': ((w*h) >> (h_shift + v_shift))*bpv
            })
            offset += ((w*h) >> (h_shift + v_shift))*bpv

            components.append({
                'stride': (w >> h_shift)*bpv,
                'offset': offset,
                'width': w >> h_shift,
                'height': h >> v_shift,
                'length': ((w*h) >> (h_shift + v_shift))*bpv
            })
            offset += ((w*h) >> (h_shift + v_shift))*bpv

        else:
            if fmt in (CogFrameFormat.YUYV,
                       CogFrameFormat.UYVY,
                       CogFrameFormat.AYUV):
                components.append({
                    'stride': w*2,
                    'offset': 0,
                    'width': w,
                    'height': h,
                    'length': h*w*2
                })
            elif fmt in (CogFrameFormat.RGBx,
                         CogFrameFormat.RGBA,
                         CogFrameFormat.xRGB,
                         CogFrameFormat.ARGB,
                         CogFrameFormat.BGRx,
                         CogFrameFormat.BGRA,
                         CogFrameFormat.xBGR,
                         CogFrameFormat.ABGR):
                components.append({
                    'stride': w*4,
                    'offset': 0,
                    'width': w,
                    'height': h,
                    'length': h*w*4
                })
            elif fmt == CogFrameFormat.RGB:
                components.append({
                    'stride': w*3,
                    'offset': 0,
                    'width': w,
                    'height': h,
                    'length': h*w*3
                })
            elif fmt == CogFrameFormat.v210:
                components.append({
                    'stride': (((w + 47) // 48) * 128),
                    'offset': 0,
                    'width': w,
                    'height': h,
                    'length': h*(((w + 47) // 48) * 128)
                })
            elif fmt == CogFrameFormat.v216:
                components.append({
                    'stride': w*4,
                    'offset': 0,
                    'width': w,
                    'height': h,
                    'length': h*w*4
                })
        return components

    if ("cog_frame" in meta['grain'] and
        ("components" not in meta['grain']['cog_frame'] or
         len(meta['grain']['cog_frame']['components']) == 0)):
        meta['grain']['cog_frame']['components'] = components_for_format(cog_frame_format, width, height)

    return VIDEOGRAIN(meta, data)


@overload
def CodedVideoGrain(src_id_or_meta: CodedVideoGrainMetadataDict,
                    flow_id_or_data: GrainDataParameterType = None) -> CODEDVIDEOGRAIN: ...


@overload
def CodedVideoGrain(src_id_or_meta: Optional[UUID] = None,
                    flow_id_or_data: Optional[UUID] = None,
                    origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                    creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                    sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                    rate: Fraction = Fraction(25, 1),
                    duration: Fraction = Fraction(1, 25),
                    cog_frame_format: CogFrameFormat = CogFrameFormat.UNKNOWN,
                    origin_width: int = 1920,
                    origin_height: int = 1080,
                    coded_width: Optional[int] = None,
                    coded_height: Optional[int] = None,
                    is_key_frame: bool = False,
                    temporal_offset: int = 0,
                    length: Optional[int] = None,
                    cog_frame_layout: CogFrameLayout = CogFrameLayout.UNKNOWN,
                    unit_offsets: Optional[List[int]] = None,
                    src_id: Optional[UUID] = None,
                    source_id: Optional[UUID] = None,
                    format: Optional[CogFrameFormat] = None,
                    layout: Optional[CogFrameLayout] = None,
                    flow_id: Optional[UUID] = None,
                    data: GrainDataParameterType = None) -> CODEDVIDEOGRAIN: ...


def CodedVideoGrain(src_id_or_meta=None,
                    flow_id_or_data=None,
                    origin_timestamp=None,
                    creation_timestamp=None,
                    sync_timestamp=None,
                    rate=Fraction(25, 1),
                    duration=Fraction(1, 25),
                    cog_frame_format=CogFrameFormat.UNKNOWN,
                    origin_width=1920,
                    origin_height=1080,
                    coded_width=None,
                    coded_height=None,
                    is_key_frame=False,
                    temporal_offset=0,
                    length=None,
                    cog_frame_layout=CogFrameLayout.UNKNOWN,
                    unit_offsets=None,
                    src_id=None,
                    source_id=None,
                    format=None,
                    layout=None,
                    flow_id=None,
                    data=None):
    """\
Function called to construct a coded video grain either from existing data or with new data.

First method of calling:

    CodedVideoGrain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for a Video Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "cog_coded_frame": {
                    "format": cog_frame_format, # int or CogFrameFormat
                    "origin_width": origin_width, # int
                    "origin_height": origin_height, # int
                    "coded_width": coded_width, # int
                    "coded_height": coded_height, # int
                    "layout": cog_frame_layout, # int or CogFrameLayout
                    "is_key_frame": False, # bool
                    "temporal_offset": temporal_offset, # int
                    "unit_offsets": [0, 16, 27] # list of int (optional)
                }
            }
        }

Alternatively it may be called as:

    CodedVideoGrain(src_id, flow_id,
                    origin_timestamp=None,
                    sync_timestamp=None,
                    rate=Fraction(25, 1),
                    duration=Fraction(1, 25),
                    cog_frame_format=CogFrameFormat.UNKNOWN,
                    origin_width=1920,
                    origin_height=1080,
                    is_key_frame=False,
                    coded_width=None,
                    coded_height=None,
                    temporal_offset=0,
                    length=None,
                    cog_frame_layout=CogFrameLayout.UNKNOWN,
                    unit_offsets=None,
                    data=None):

in which case a new grain will be constructed with type "coded_video" and the
specified metadata. If the data argument is None and the length argument is not
then a new bytearray object will be constructed with size equal to length.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.CODEDVIDEOGRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    meta: Optional[CodedVideoGrainMetadataDict] = None

    if cog_frame_format is None:
        cog_frame_format = format
    if source_id is not None:
        src_id = source_id
    if cog_frame_layout is None:
        cog_frame_layout = layout

    if isinstance(src_id_or_meta, dict):
        meta = cast(CodedVideoGrainMetadataDict, src_id_or_meta)
        if data is None and not isinstance(flow_id_or_data, UUID):
            data = flow_id_or_data
    else:
        if src_id is None and isinstance(src_id_or_meta, UUID):
            src_id = src_id_or_meta
        if flow_id is None and isinstance(flow_id_or_data, UUID):
            flow_id = flow_id_or_data

    if coded_width is None:
        coded_width = origin_width
    if coded_height is None:
        coded_height = origin_height

    if length is None:
        if data is not None and hasattr(data, "__len__"):
            length = len(cast(Sized, data))
        else:
            length = 0

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = creation_timestamp

        if cts is None:
            cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "coded_video",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(mediatimestamp(origin_timestamp)),
                "sync_timestamp": str(mediatimestamp(sync_timestamp)),
                "creation_timestamp": str(mediatimestamp(cts)),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "cog_coded_frame": {
                    "format": cog_frame_format,
                    "origin_width": origin_width,
                    "origin_height": origin_height,
                    "coded_width": coded_width,
                    "coded_height": coded_height,
                    "layout": cog_frame_layout,
                    "is_key_frame": is_key_frame,
                    "temporal_offset": temporal_offset
                }
            },
        }

    if data is None:
        data = bytearray(length)

    if "grain" in meta and "cog_coded_frame" in meta['grain'] and unit_offsets is not None:
        meta['grain']['cog_coded_frame']['unit_offsets'] = unit_offsets

    return CODEDVIDEOGRAIN(meta, data)


@overload
def EventGrain(src_id_or_meta: EventGrainMetadataDict,
               flow_id_or_data: GrainDataParameterType = None) -> EVENTGRAIN: ...


@overload
def EventGrain(src_id_or_meta: Optional[UUID] = None,
               flow_id_or_data: Optional[UUID] = None,
               origin_timestamp: Optional[SupportsMediaTimestamp] = None,
               creation_timestamp: Optional[SupportsMediaTimestamp] = None,
               sync_timestamp: Optional[SupportsMediaTimestamp] = None,
               rate: Fraction = Fraction(25, 1),
               duration: Fraction = Fraction(1, 25),
               event_type: str = '',
               topic: str = '',
               src_id: Optional[UUID] = None,
               source_id: Optional[UUID] = None,
               flow_id: Optional[UUID] = None,
               meta: Optional[EventGrainMetadataDict] = None,
               data: GrainDataParameterType = None) -> EVENTGRAIN: ...


def EventGrain(src_id_or_meta=None,
               flow_id_or_data=None,
               origin_timestamp=None,
               creation_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               event_type='',
               topic='',
               src_id=None,
               source_id=None,
               flow_id=None,
               meta=None,
               data=None):
    """\
Function called to construct an event grain either from existing data or with new data.

First method of calling:

    EventGrain(meta, data=None)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains a string representation of the json grain payload.

Optionally the data element can be replaced with an Awaitable that will return a
data element when awaited. This is useful for grains that are backed with some
sort of asynchronous IO system.

A properly formated metadata dictionary for an Event Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "event",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "event_payload": {
                    "type": event_type, # str
                    "topic": topic, # str
                    "data": [
                        {
                            "path": path, # str
                            "pre": pre, # any json serialisable object (may be ommitted)
                            "post": post  # any json serialisable object (may be ommitted)
                        }
                    ]
                }
            }
        }

If the "data" parameter is a bytes-like object from which a json object can be deserialised then it will be
inserted into the metadata dictionary at the key "event_payload".

Alternatively it may be called as:

    EventGrain(src_id, flow_id,
               origin_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               event_type='',
               topic='',
               data=None):

in which case a new grain will be constructed with type "event" and the
specified metadata. If the "data" parameter is a bytes-like object from which a
json object can be deserialised then it will be inserted into the metadata
dictionary at the key "event_payload". If no data object is provided then the
"data" array will be left as an empty list.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.EVENTGRAIN

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    if source_id is not None:
        src_id = source_id

    if isinstance(src_id_or_meta, dict):
        if meta is None and not isinstance(src_id_or_meta, UUID):
            meta = src_id_or_meta
        if data is None and not isinstance(flow_id_or_data, UUID):
            data = flow_id_or_data
    else:
        if src_id is None and isinstance(src_id_or_meta, UUID):
            src_id = src_id_or_meta
        if flow_id is None and isinstance(flow_id_or_data, UUID):
            flow_id = flow_id_or_data

    if meta is None:
        if src_id is None or flow_id is None:
            raise AttributeError("Must include either metadata, or src_id, and flow_id")

        cts = creation_timestamp
        if cts is None:
            cts = Timestamp.get_time()
        if origin_timestamp is None:
            origin_timestamp = cts
        if sync_timestamp is None:
            sync_timestamp = origin_timestamp
        meta = EventGrainMetadataDict({
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "event",
                "source_id": str(src_id),
                "flow_id": str(flow_id),
                "origin_timestamp": str(mediatimestamp(origin_timestamp)),
                "sync_timestamp": str(mediatimestamp(sync_timestamp)),
                "creation_timestamp": str(mediatimestamp(cts)),
                "rate": {
                    "numerator": Fraction(rate).numerator,
                    "denominator": Fraction(rate).denominator,
                    },
                "duration": {
                    "numerator": Fraction(duration).numerator,
                    "denominator": Fraction(duration).denominator,
                    },
                "event_payload": {
                    "type": event_type,
                    "topic": topic,
                    "data": []
                }
            },
        })

    return EVENTGRAIN(meta, data)
