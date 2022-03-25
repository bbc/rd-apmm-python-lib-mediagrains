from uuid import UUID
from mediatimestamp.immutable import Timestamp, SupportsMediaTimestamp, mediatimestamp, TimeOffset
from fractions import Fraction

from typing import (
    Optional)
from ..typing import (
    AudioGrainMetadataDict,
    GrainDataParameterType)

from ..cogenums import CogAudioFormat
from .Grain import Grain


def size_for_audio_format(cog_audio_format: CogAudioFormat, channels: int, samples: int) -> int:
    if (cog_audio_format & 0x200) == 0x200:  # compressed format, no idea of correct size
        return 0

    if (cog_audio_format & 0x3) == 0x1:
        channels += 1
        channels //= 2
        channels *= 2
    if (cog_audio_format & 0xC) == 0xC:
        depth = 8
    elif (cog_audio_format & 0xf) == 0x04:
        depth = 4
    else:
        depth = ((cog_audio_format & 0xf) >> 2) + 2
    return channels * samples * depth


class AudioGrain(Grain):
    """\
A class representing a raw audio grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is the data element described below..

The Grain class provides a number of properties which can be used to access
parts of the standard grain metadata, and this class inherits these:

meta
    The meta dictionary object

data
    Either None or an object which can be cast to bytes by passing it to the bytes
    constructor and will in of itself respond to the python-level portions of the bytes-like
    object protocol. It is not guaranteed that this object will always respond correctly to the
    C buffer-protocol, but it can always be converted into something that will by calling bytes on it.

grain_type
    A string containing the type of the grain, always "audio"

src_id
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
    The length of the data element or 0 if that is None

The AudioGrain class also provides additional properies

format
    An enumerated value of type CogAudioFormat

samples
    The number of audio samples per channel in this grain

channels
    The number of channels in this grain

sample_rate
    An integer indicating the number of samples per channel per second in this
    audio flow.
"""
    def __init__(self,
                 meta: AudioGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
                 src_id: Optional[UUID] = None,
                 flow_id: Optional[UUID] = None,
                 origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                 sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                 creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                 rate: Fraction = Fraction(25, 1),
                 duration: Fraction = Fraction(1, 25),
                 cog_audio_format: CogAudioFormat = CogAudioFormat.INVALID,
                 samples: int = 0,
                 channels: int = 0,
                 sample_rate: int = 48000):

        if meta is None:
            if src_id is None:
                raise AttributeError("src_id is None. Meta is None so src_id must not be None.")
            if flow_id is None:
                raise AttributeError("flow_id is None. Meta is None so flow_id must not be None.")

            if not isinstance(src_id, UUID):
                raise AttributeError(f"src_id: Seen type {type(src_id)}, expected UUID.")
            if not isinstance(flow_id, UUID):
                raise AttributeError(f"flow_id: Seen type {type(flow_id)}, expected UUID.")

            if creation_timestamp is None:
                creation_timestamp = Timestamp.get_time()
            if origin_timestamp is None:
                origin_timestamp = creation_timestamp
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
                    'creation_timestamp': str(mediatimestamp(creation_timestamp)),
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

        super().__init__(meta, data)
        self.meta: AudioGrainMetadataDict

        self._factory = "AudioGrain"
        self.meta['grain']['grain_type'] = 'audio'
        if 'cog_audio' not in self.meta['grain']:
            self.meta['grain']['cog_audio'] = {}  # type: ignore
        if 'format' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['format'] = int(CogAudioFormat.INVALID)
        if 'samples' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['samples'] = 0
        if 'channels' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['channels'] = 0
        if 'sample_rate' not in self.meta['grain']['cog_audio']:
            self.meta['grain']['cog_audio']['sample_rate'] = 0
        self.meta['grain']['cog_audio']['format'] = int(self.meta['grain']['cog_audio']['format'])

    def final_origin_timestamp(self) -> Timestamp:
        return (self.origin_timestamp + TimeOffset.from_count(self.samples - 1, self.sample_rate, 1))

    @property
    def format(self) -> CogAudioFormat:
        return CogAudioFormat(self.meta['grain']['cog_audio']['format'])

    @format.setter
    def format(self, value: CogAudioFormat) -> None:
        self.meta['grain']['cog_audio']['format'] = int(value)

    @property
    def cog_audio_format(self) -> CogAudioFormat:
        return CogAudioFormat(self.meta['grain']['cog_audio']['format'])

    @cog_audio_format.setter
    def cog_audio_format(self, value: CogAudioFormat) -> None:
        self.meta['grain']['cog_audio']['format'] = int(value)

    @property
    def samples(self) -> int:
        return self.meta['grain']['cog_audio']['samples']

    @samples.setter
    def samples(self, value: int) -> None:
        self.meta['grain']['cog_audio']['samples'] = int(value)

    @property
    def channels(self) -> int:
        return self.meta['grain']['cog_audio']['channels']

    @channels.setter
    def channels(self, value: int) -> None:
        self.meta['grain']['cog_audio']['channels'] = int(value)

    @property
    def sample_rate(self) -> int:
        return self.meta['grain']['cog_audio']['sample_rate']

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self.meta['grain']['cog_audio']['sample_rate'] = int(value)

    @property
    def expected_length(self) -> int:
        return size_for_audio_format(self.format, self.channels, self.samples)

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.sample_rate:
            return Fraction(self.sample_rate, 1)
        else:
            return None
