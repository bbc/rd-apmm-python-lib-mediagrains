from uuid import UUID
from mediatimestamp.immutable import (
    Timestamp,
    SupportsMediaTimestamp,
    mediatimestamp)
from fractions import Fraction
from .BaseGrain import BaseGrain
from .VideoGrain import VideoGrain
from .AudioGrain import AudioGrain
from .CodedVideoGrain import CodedVideoGrain
from .CodedAudioGrain import CodedAudioGrain
from .EventGrain import EventGrain

from typing import (
    Optional,
    cast)

from ..typing import (
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    EventGrainMetadataDict,
    GrainMetadataDict,
    EmptyGrainMetadataDict,
    GrainDataParameterType,
    VideoGrainMetadataDict)


class Grain(BaseGrain):
    """\
A factory for grains. Use when you want a generic Grain or do not know the type of grain you want to instantiate.


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
            A = super().__new__(BaseGrain)
            A.__init__(meta, data)  # type: ignore
            return A
