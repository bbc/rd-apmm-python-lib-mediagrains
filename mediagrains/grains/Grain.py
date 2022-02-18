from enum import IntEnum
from uuid import UUID
from mediatimestamp.immutable import (
    Timestamp,
    TimeOffset,
    TimeRange,
    SupportsMediaTimeOffset,
    SupportsMediaTimestamp,
    mediatimeoffset,
    mediatimestamp)
from collections.abc import Sequence, MutableSequence, Mapping
from fractions import Fraction
from copy import copy, deepcopy
from inspect import isawaitable
from .BaseGrain import BaseGrain
from .VideoGrain import VideoGrain
from .AudioGrain import AudioGrain
from .CodedVideoGrain import CodedVideoGrain
from .CodedAudioGrain import CodedAudioGrain
from .EventGrain import EventGrain

from typing import (
    List,
    Dict,
    Any,
    TypeAlias,
    Union,
    SupportsBytes,
    Optional,
    overload,
    Tuple,
    cast,
    Sized,
    Iterator,
    Iterable,
    Awaitable,
    Generator)

from ..typing import (
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    EventGrainMetadataDict,
    RationalTypes,
    GrainMetadataDict,
    GrainDataType,
    EmptyGrainMetadataDict,
    FractionDict,
    TimeLabel,
    GrainDataParameterType,
    VideoGrainMetadataDict)


class Grain(BaseGrain):
    """\
A class representing a generic media grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is None or one of the following:
* a bytes-like object
* An object supporting the __bytes__ magic method
* An awaitable returning a valid data element

In addition the class provides a number of properties which can be used to
access parts of the standard grain metadata, and all other grain classes
inherit these:

meta
    The meta dictionary object

data
    One of the following:
        * A byteslike object -- This becomes the grain's data element
        * An object that has a method __bytes__ which returns a bytes-like object, which will be the grain's data
          element
        * None -- This grain has no data

    If the data parameter passed on construction is an awaitable which will return a valid data element when awaited
    then the grain's data element is
    initially None, but the grain can be awaited to populate it

    For convenience any grain can be awaited and will return the data element, regardless of whether the underlying
    data is asynchronous or not

    For additional convenience using a grain as an async context manager will ensure that the data element is populated
    if it needs to be and can be.

grain_type
    A string containing the type of the grain, any value is possible

source_id
    A uuid.UUID object representing the source_id in the grain

flow_id
    A uuid.UUID object representing the flow_id in the grain

origin_timestamp
    An mediatimestamp.Timestamp object representing the origin timestamp
    of this grain.

sync_timestamp
    An mediatimestamp.Timestamp object representing the sync timestamp
    of this grain.

creation_timestamp
    An mediatimestamp.Timestamp object representing the creation timestamp
    of this grain.

rate
    A fractions.Fraction object representing the grain rate in grains per second.

duration
    A fractions.Fraction object representing the grain duration in seconds.

timelabels
    A list object containing time label data

length
    The length of the data property, or 0 if it is None

expected_length
    How long the data would be expected to be based on what's listed in the metadata


In addition these methods are provided for convenience:


final_origin_timestamp()
    The origin timestamp of the final sample in the grain. For most grain types this is the same as
    origin_timestamp, but not for audio grains.

origin_timerange()
    The origin time range covered by the samples in the grain.

normalise_time(value)
    Returns a normalised Timestamp, TimeOffset or TimeRange using the media rate.

media_rate
    The video frame rate or audio sample rate as a Fraction or None. Returns None if there is no media
    rate or the media rate == 0.

    """
    def __new__(cls,
                meta: Optional[GrainMetadataDict] = None,
                data: GrainDataParameterType = None,
                src_id: Optional[UUID] = None,
                flow_id: Optional[UUID] = None,
                origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                rate: Fraction = Fraction(0, 1),
                duration: Fraction = Fraction(0, 1)):

        if meta is None:
            if creation_timestamp is None:
                creation_timestamp = Timestamp.get_time()

            if origin_timestamp is None:
                origin_timestamp = creation_timestamp
            if sync_timestamp is None:
                sync_timestamp = origin_timestamp

            if src_id is None:
                raise AttributeError("src_id is None. Meta is None so src_id must not be None.")
            if flow_id is None:
                raise AttributeError("flow_id is None. Meta is None so flow_id must not be None.")

            if not isinstance(src_id, UUID):
                raise AttributeError(f"src_id: Seen type {type(src_id)}, expected UUID.")
            if not isinstance(flow_id, UUID):
                raise AttributeError(f"flow_id: Seen type {type(flow_id)}, expected UUID.")

            meta = EmptyGrainMetadataDict({
                "@_ns": "urn:x-ipstudio:ns:0.1",
                "grain": {
                    'grain_type': "empty",
                    'source_id': str(src_id),
                    'flow_id': str(flow_id),
                    'origin_timestamp': str(mediatimestamp(origin_timestamp)),
                    'sync_timestamp': str(mediatimestamp(sync_timestamp)),
                    'creation_timestamp': str(mediatimestamp(creation_timestamp)),
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

        if 'grain' in meta and 'grain_type' in meta['grain']:
            match meta['grain']['grain_type']:
                case 'video':
                    return VideoGrain(cast(VideoGrainMetadataDict, meta), data)
                case 'audio':
                    return AudioGrain(cast(AudioGrainMetadataDict, meta), data)
                case 'coded_video':
                    return CodedVideoGrain(cast(CodedVideoGrainMetadataDict, meta), data)
                case 'coded_audio':
                    return CodedAudioGrain(cast(CodedAudioGrainMetadataDict, meta), data)
                case 'event' | 'data':
                    return EventGrain(cast(EventGrainMetadataDict, meta), data)
                case 'empty':
                    A = super().__new__(BaseGrain)
                    A.__init__(meta, data)
                    return A
        else:
            A = super().__new__(BaseGrain)
            A.__init__(meta, data)
            return A

