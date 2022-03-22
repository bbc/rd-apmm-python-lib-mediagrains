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

from typing import (
    List,
    Dict,
    Any,
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
    RationalTypes,
    GrainDataType,
    FractionDict,
    TimeLabel)

from ..typing import (
    AudioGrainMetadataDict,
    CodedAudioGrainMetadataDict,
    CodedVideoGrainMetadataDict,
    EventGrainMetadataDict,
    GrainMetadataDict,
    EmptyGrainMetadataDict,
    GrainDataParameterType,
    VideoGrainMetadataDict)


class GrainType(IntEnum):
    Grain = 0,
    VIDEOGrain = 1,
    AUDIOGrain = 2,
    CODEDVIDEOGrain = 3,
    CODEDAUDIOGrain = 4,
    EVENTGrain = 5


def GrainFactory(meta: Optional[GrainMetadataDict] = None,
                 data: GrainDataParameterType = None,
                 src_id: Optional[UUID] = None,
                 flow_id: Optional[UUID] = None,
                 origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                 sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                 creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                 rate: Fraction = Fraction(0, 1),
                 duration: Fraction = Fraction(0, 1),
                 **kwargs):
    from .VideoGrain import VideoGrain
    from .AudioGrain import AudioGrain
    from .CodedVideoGrain import CodedVideoGrain
    from .CodedAudioGrain import CodedAudioGrain
    from .EventGrain import EventGrain
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
        return Grain(cast(GrainMetadataDict, meta), data)


def _stringify_timestamp_input(value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> str:
    if isinstance(value, SupportsMediaTimestamp):
        value = mediatimestamp(value).to_sec_nsec()
    elif isinstance(value, SupportsMediaTimeOffset):
        value = mediatimeoffset(value).to_sec_nsec()
    elif not isinstance(value, str):
        raise ValueError(
            f"{repr(value)} is not a type that can be converted to a Timestamp or TimeOffset, nor is it a string.")

    return value


# For use in 'new style' grain init. Can be removed once old style is excised.
def new_attributes_for_grain_type(grain_type: str | GrainType):
    return(attributes_for_grain_type(grain_type=grain_type, new=True))


# As above, the 'new' parameter will give 'new style' grain init info. 'x if not new else' statements can be removed
# once 'old style' is excised.
def attributes_for_grain_type(grain_type: str | GrainType, new: bool = False) -> List[str]:
    """Returns a list of attributes for a particular grain type. Useful for testing."""
    # cast to the correct string
    if type(grain_type) is GrainType:
        grain_type = ["grain", "video", "audio", "coded_video", "coded_audio", "event"][grain_type]

    COMMON_ATTRS = ['source_id' if not new else "src_id", 'flow_id', 'origin_timestamp', 'sync_timestamp',
                    'creation_timestamp', 'rate', 'duration']
    if grain_type == "event":
        return COMMON_ATTRS + ["event_type", "topic", "event_data"]
    elif grain_type == "audio":
        return COMMON_ATTRS + ["format" if not new else "cog_audio_format", "samples", "channels", "sample_rate"]
    elif grain_type == "coded_audio":
        return COMMON_ATTRS + ["format" if not new else "cog_audio_format", "samples", "channels", "sample_rate",
                               "priming", "remainder"]
    elif grain_type == "coded_video":
        return COMMON_ATTRS + ["format" if not new else "cog_frame_format", "coded_width", "coded_height",
                               "layout" if not new else "cog_frame_layout", "origin_width", "origin_height",
                               "is_key_frame", "temporal_offset", "unit_offsets"]
    elif grain_type == "video":
        return COMMON_ATTRS + ["format" if not new else "cog_frame_format", "width", "height",
                               "layout" if not new else "cog_frame_layout"]
    else:
        return COMMON_ATTRS


class Grain(Sequence):
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
    def __init__(self, meta: GrainMetadataDict, data: GrainDataParameterType, **kwargs):

        self.meta = meta

        if meta is None:
            pass

        self._data_fetcher_coroutine: Optional[Awaitable[Optional[GrainDataType]]]
        self._data_fetcher_length: int = 0
        self._data: Optional[GrainDataType]

        if isawaitable(data):
            self._data_fetcher_coroutine = cast(Awaitable[Optional[GrainDataType]], data)
            self._data = None
        else:
            self._data_fetcher_coroutine = None
            self._data = cast(Optional[GrainDataType], data)
        self._factory = "Grain"
        if self.meta is not None:
            # This code is here to deal with malformed inputs, and as such needs to cast away the type safety to operate
            if "@_ns" not in self.meta:
                cast(EmptyGrainMetadataDict, self.meta)['@_ns'] = "urn:x-ipstudio:ns:0.1"
            if 'grain' not in self.meta:
                cast(dict, self.meta)['grain'] = {}
            if 'grain_type' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['grain_type'] = "empty"
            if 'creation_timestamp' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = str(Timestamp.get_time())
            if 'origin_timestamp' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta
                     )['grain']['origin_timestamp'] = self.meta['grain']['creation_timestamp']
            if 'sync_timestamp' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = \
                                                        self.meta['grain']['origin_timestamp']
            if 'rate' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {'numerator': 0,
                                                                            'denominator': 1}
            if 'duration' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {'numerator': 0,
                                                                                'denominator': 1}
            if 'source_id' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = "00000000-0000-0000-0000-000000000000"
            if 'flow_id' not in self.meta['grain']:
                cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = "00000000-0000-0000-0000-000000000000"

            if isinstance(self.meta["grain"]["source_id"], UUID):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = str(self.meta['grain']['source_id'])
            if isinstance(self.meta["grain"]["flow_id"], UUID):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = str(self.meta['grain']['flow_id'])
            if not isinstance(self.meta["grain"]["origin_timestamp"], str):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['origin_timestamp'] = _stringify_timestamp_input(
                    self.meta['grain']['origin_timestamp'])
            if not isinstance(self.meta["grain"]["sync_timestamp"], str):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = _stringify_timestamp_input(
                    self.meta['grain']['sync_timestamp'])
            if not isinstance(self.meta["grain"]["creation_timestamp"], str):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = _stringify_timestamp_input(
                    self.meta['grain']['creation_timestamp'])
            if isinstance(self.meta['grain']['rate'], Fraction):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {
                    'numerator': self.meta['grain']['rate'].numerator,
                    'denominator': self.meta['grain']['rate'].denominator}
            if isinstance(self.meta['grain']['duration'], Fraction):
                cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {
                    'numerator': self.meta['grain']['duration'].numerator,
                    'denominator': self.meta['grain']['duration'].denominator}
        else:
            raise ValueError("Metadata dict passed to Grain was none!!")

    def __len__(self) -> int:
        return 2

    @overload
    def __getitem__(self, index: int) -> Union[GrainMetadataDict, Optional[GrainDataType]]: ...

    @overload  # noqa: F811
    def __getitem__(self, index: slice) -> Union[Tuple[GrainMetadataDict],
                                                 Tuple[GrainMetadataDict, Optional[GrainDataType]],
                                                 Tuple[Optional[GrainDataType]],
                                                 Tuple[()]]: ...

    def __getitem__(self, index):  # noqa: F811
        return (self.meta, self.data)[index]

    def __repr__(self) -> str:
        if not hasattr(self.data, "__len__"):
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< binary data of length {} >)".format(self._factory, self.meta, len(cast(Sized, self.data)))

    def __eq__(self, other: object) -> bool:
        return tuple(self) == other

    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __copy__(self) -> "Grain":
        return GrainFactory(copy(self.meta), self.data)

    def __deepcopy__(self, memo) -> "Grain":
        return GrainFactory(deepcopy(self.meta), deepcopy(self.data))

    def __bytes__(self) -> Optional[bytes]:
        if isinstance(self._data, bytes):
            return self._data
        elif self._data is None:
            return None
        return bytes(self._data)

    def has_data(self) -> bool:
        return self._data is not None

    def __await__(self) -> Generator[Any, None, Optional[GrainDataType]]:
        async def __inner():
            if self._data is None and self._data_fetcher_coroutine is not None:
                self._data = await self._data_fetcher_coroutine
            return self._data
        return __inner().__await__()

    async def __aenter__(self):
        await self
        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    @property
    def data(self) -> Optional[GrainDataType]:
        return self._data

    @data.setter
    def data(self, value: GrainDataParameterType):
        if isawaitable(value):
            self._data = None
            self._data_fetcher_coroutine = cast(Awaitable[Optional[GrainDataType]], value)
        else:
            self._data = cast(Optional[GrainDataType], value)
            self._data_fetcher_coroutine = None

    @property
    def grain_type(self) -> str:
        if not hasattr(self, 'meta'):
            pass
        return self.meta['grain']['grain_type']

    @grain_type.setter
    def grain_type(self, value: str) -> None:
        # We ignore the type safety rules for this assignment
        self.meta['grain']['grain_type'] = value  # type: ignore

    @property
    def source_id(self) -> UUID:
        # Our code ensures that this will always be a string at runtime
        return UUID(cast(str, self.meta['grain']['source_id']))

    @source_id.setter
    def source_id(self, value: Union[UUID, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = str(value)

    @property
    def src_id(self) -> UUID:
        # Our code ensures that this will always be a string at runtime
        return UUID(cast(str, self.meta['grain']['source_id']))

    @src_id.setter
    def src_id(self, value: Union[UUID, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['source_id'] = str(value)

    @property
    def flow_id(self) -> UUID:
        return UUID(cast(str, self.meta['grain']['flow_id']))

    @flow_id.setter
    def flow_id(self, value: Union[UUID, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['flow_id'] = str(value)

    @property
    def origin_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['origin_timestamp']))

    @origin_timestamp.setter
    def origin_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]):
        cast(EmptyGrainMetadataDict, self.meta)['grain']['origin_timestamp'] = _stringify_timestamp_input(value)

    def final_origin_timestamp(self) -> Timestamp:
        return self.origin_timestamp

    def origin_timerange(self) -> TimeRange:
        return TimeRange(self.origin_timestamp, self.final_origin_timestamp(), TimeRange.INCLUSIVE)

    @overload
    def normalise_time(self, value: TimeOffset) -> TimeOffset: ...

    @overload
    def normalise_time(self, value: TimeRange) -> TimeRange: ...

    def normalise_time(self, value):
        if self.media_rate is not None:
            return value.normalise(self.media_rate.numerator, self.media_rate.denominator)
        else:
            return value

    @property
    def media_rate(self) -> Optional[Fraction]:
        return None

    @property
    def sync_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['sync_timestamp']))

    @sync_timestamp.setter
    def sync_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['sync_timestamp'] = _stringify_timestamp_input(value)

    @property
    def creation_timestamp(self) -> Timestamp:
        return Timestamp.from_tai_sec_nsec(cast(str, self.meta['grain']['creation_timestamp']))

    @creation_timestamp.setter
    def creation_timestamp(self, value: Union[SupportsMediaTimestamp, SupportsMediaTimeOffset, str]) -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['creation_timestamp'] = _stringify_timestamp_input(value)

    @property
    def rate(self) -> Fraction:
        return Fraction(cast(FractionDict, self.meta['grain']['rate'])['numerator'],
                        cast(FractionDict, self.meta['grain']['rate'])['denominator'])

    @rate.setter
    def rate(self, value: RationalTypes) -> None:
        value = Fraction(value)
        cast(EmptyGrainMetadataDict, self.meta)['grain']['rate'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
        }

    @property
    def duration(self) -> Fraction:
        return Fraction(cast(FractionDict, self.meta['grain']['duration'])['numerator'],
                        cast(FractionDict, self.meta['grain']['duration'])['denominator'])

    @duration.setter
    def duration(self, value: RationalTypes) -> None:
        value = Fraction(value)
        cast(EmptyGrainMetadataDict, self.meta)['grain']['duration'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
        }

    @property
    def timelabels(self) -> "Grain.TIMELABELS":
        return Grain.TIMELABELS(self)

    @timelabels.setter
    def timelabels(self, value: "Union[List[Grain.TIMELABEL], Grain.TIMELABELS]") -> None:
        cast(EmptyGrainMetadataDict, self.meta)['grain']['timelabels'] = []
        for x in value:
            self.timelabels.append(x)

    def add_timelabel(self, tag: str, count: int, rate: Fraction, drop_frame: bool = False) -> None:
        tl = Grain.TIMELABEL()
        tl.tag = tag
        tl.count = count
        tl.rate = rate
        tl.drop_frame = drop_frame
        self.timelabels.append(tl)

    class TIMELABEL(Mapping):
        GrainMetadataDict = Dict[str, Any]

        def __init__(self, meta: "Optional[Grain.TIMELABEL.GrainMetadataDict]" = None):
            if meta is None:
                meta = {}
            self.meta = meta
            if 'tag' not in self.meta:
                self.meta['tag'] = ''
            if 'timelabel' not in self.meta:
                self.meta['timelabel'] = {}
            if 'frames_since_midnight' not in self.meta['timelabel']:
                self.meta['timelabel']['frames_since_midnight'] = 0
            if 'frame_rate_numerator' not in self.meta['timelabel']:
                self.meta['timelabel']['frame_rate_numerator'] = 0
            if 'frame_rate_denominator' not in self.meta['timelabel']:
                self.meta['timelabel']['frame_rate_denominator'] = 1
            if 'drop_frame' not in self.meta['timelabel']:
                self.meta['timelabel']['drop_frame'] = False

        def __getitem__(self, key: str) -> Union[str, Dict[str, Union[int, bool]]]:
            return self.meta[key]

        def __setitem__(self, key: str, value: Union[str, Dict[str, Union[int, bool]]]) -> None:
            if key not in ['tag', 'timelabel']:
                raise KeyError
            self.meta[key] = value

        def __iter__(self) -> Iterator[str]:
            return self.meta.__iter__()

        def __len__(self) -> int:
            return 2

        def __eq__(self, other: object) -> bool:
            return dict(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        @property
        def tag(self) -> str:
            return self.meta['tag']

        @tag.setter
        def tag(self, value: str) -> None:
            self.meta['tag'] = value

        @property
        def count(self) -> int:
            return self.meta['timelabel']['frames_since_midnight']

        @count.setter
        def count(self, value: int) -> None:
            self.meta['timelabel']['frames_since_midnight'] = int(value)

        @property
        def rate(self) -> Fraction:
            return Fraction(self.meta['timelabel']['frame_rate_numerator'],
                            self.meta['timelabel']['frame_rate_denominator'])

        @rate.setter
        def rate(self, value: RationalTypes) -> None:
            value = Fraction(value)
            self.meta['timelabel']['frame_rate_numerator'] = value.numerator
            self.meta['timelabel']['frame_rate_denominator'] = value.denominator

        @property
        def drop_frame(self) -> bool:
            return self.meta['timelabel']['drop_frame']

        @drop_frame.setter
        def drop_frame(self, value: bool) -> None:
            self.meta['timelabel']['drop_frame'] = bool(value)

    class TIMELABELS(MutableSequence):
        def __init__(self, parent: "Grain"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> "Grain.TIMELABEL": ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> "List[Grain.TIMELABEL]": ...

        def __getitem__(self, key):  # noqa: F811
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list index out of range")
            if isinstance(key, int):
                return Grain.TIMELABEL(self.parent.meta['grain']['timelabels'][key])
            else:
                return [Grain.TIMELABEL(self.parent.meta['grain']['timelabels'][n]) for n in range(len(self))[key]]

        @overload
        def __setitem__(self, key: int, value: "Grain.TIMELABEL.GrainMetadataDict") -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: "Iterable[Grain.TIMELABEL.GrainMetadataDict]") -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")
            if isinstance(key, int):
                self.parent.meta['grain']['timelabels'][key] = dict(Grain.TIMELABEL(value))
            else:
                values = iter(value)
                for n in key:
                    self.parent.meta['grain']['timelabels'][n] = dict(Grain.TIMELABEL(next(values)))

        def __delitem__(self, key: Union[int, slice]) -> None:
            if 'timelabels' not in self.parent.meta['grain']:
                raise IndexError("list assignment index out of range")

            del self.parent.meta['grain']['timelabels'][key]
            if len(self.parent.meta['grain']['timelabels']) == 0:
                del self.parent.meta['grain']['timelabels']

        def insert(self, key: int, value: "Grain.TIMELABEL.GrainMetadataDict") -> None:
            if 'timelabels' not in self.parent.meta['grain']:
                cast(EmptyGrainMetadataDict, self.parent.meta)['grain']['timelabels'] = []
            self.parent.meta['grain']['timelabels'].insert(key, cast(TimeLabel, dict(Grain.TIMELABEL(value))))

        def __len__(self) -> int:
            if 'timelabels' not in self.parent.meta['grain']:
                return 0
            return len(self.parent.meta['grain']['timelabels'])

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

    @property
    def length(self) -> int:
        if hasattr(self.data, "__len__"):
            return len(cast(Sized, self.data))
        elif hasattr(self.data, "__bytes__"):
            return len(bytes(cast(SupportsBytes, self.data)))
        elif self.data is None and self._data_fetcher_coroutine is not None:
            return self._data_fetcher_length
        else:
            return 0

    @length.setter
    def length(self, L: int) -> None:
        if self.data is None and self._data_fetcher_coroutine is not None:
            self._data_fetcher_length = L
        else:
            raise AttributeError

    @property
    def expected_length(self) -> int:
        if 'length' in self.meta['grain']:
            return cast(dict, self.meta['grain'])['length']
        else:
            return self.length
