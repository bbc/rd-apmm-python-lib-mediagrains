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
from mediatimestamp.immutable import SupportsMediaTimestamp
from fractions import Fraction

from typing import Optional, cast, Sized, List

from deprecated import deprecated
from .typing import (
    GrainDataParameterType,
    GrainMetadataDict,
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    VideoGrainMetadataDict,
    EventGrainMetadataDict,
    CodedVideoGrainMetadataDict)

from .cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat
from .grains import GRAIN, VIDEOGRAIN, AUDIOGRAIN, CODEDVIDEOGRAIN, CODEDAUDIOGRAIN, EVENTGRAIN, GrainFactory


__all__ = ["Grain", "VideoGrain", "AudioGrain", "CodedVideoGrain", "CodedAudioGrain", "EventGrain"]


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
def Grain(src_id_or_meta: Optional[UUID | dict] = None,
          flow_id_or_data: Optional[UUID | dict] = None,
          origin_timestamp: Optional[SupportsMediaTimestamp] = None,
          sync_timestamp: Optional[SupportsMediaTimestamp] = None,
          creation_timestamp: Optional[SupportsMediaTimestamp] = None,
          rate: Fraction = Fraction(0, 1),
          duration: Fraction = Fraction(0, 1),
          flow_id: Optional[UUID] = None,
          data: GrainDataParameterType = None,
          src_id: Optional[UUID] = None,
          source_id: Optional[UUID] = None,
          meta: Optional[GrainMetadataDict] = None) -> GRAIN:
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
            meta = cast(GrainMetadataDict, src_id_or_meta)
            src_id = None
            if data is None and not isinstance(flow_id_or_data, UUID):
                data = cast(GrainDataParameterType, flow_id_or_data)
                flow_id = None
        else:
            if src_id is None and isinstance(src_id_or_meta, UUID):
                src_id = src_id_or_meta
            if flow_id is None and isinstance(flow_id_or_data, UUID):
                flow_id = flow_id_or_data

    return GrainFactory(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                        sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                        duration=duration)


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
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
               data: GrainDataParameterType = None) -> AUDIOGRAIN:
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

    return AUDIOGRAIN(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                      sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                      duration=duration, cog_audio_format=cog_audio_format, samples=samples, channels=channels,
                      sample_rate=sample_rate)


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
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
                    data: GrainDataParameterType = None) -> CODEDAUDIOGRAIN:
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

    return CODEDAUDIOGRAIN(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                           duration=duration, cog_audio_format=cog_audio_format, samples=samples, channels=channels,
                           priming=priming, remainder=remainder, length=length, sample_rate=sample_rate)


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
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
               data: GrainDataParameterType = None) -> VIDEOGRAIN:
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

    return VIDEOGRAIN(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                      sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                      duration=duration, cog_frame_format=cog_frame_format, width=width, height=height,
                      cog_frame_layout=cog_frame_layout)


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
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
                    data: GrainDataParameterType = None) -> CODEDVIDEOGRAIN:
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

    return CODEDVIDEOGRAIN(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                           duration=duration, cog_frame_format=cog_frame_format, coded_width=coded_width,
                           coded_height=coded_height, is_key_frame=is_key_frame, temporal_offset=temporal_offset,
                           cog_frame_layout=cog_frame_layout, unit_offsets=unit_offsets, origin_height=origin_height,
                           origin_width=origin_width, length=length)


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.grains`.')
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
               data: GrainDataParameterType = None) -> EVENTGRAIN:
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

    return EVENTGRAIN(meta=meta, data=data, src_id=src_id, flow_id=flow_id, origin_timestamp=origin_timestamp,
                      sync_timestamp=sync_timestamp, creation_timestamp=creation_timestamp, rate=rate,
                      duration=duration, event_type=event_type, topic=topic)
