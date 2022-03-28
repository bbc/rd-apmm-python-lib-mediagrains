from collections.abc import MutableSequence
from fractions import Fraction

from typing import (
    List,
    Union,
    Optional,
    overload,
    cast,
    Sized,
    Iterable)
from uuid import UUID
from mediatimestamp.immutable import Timestamp, SupportsMediaTimestamp, mediatimestamp
from ..typing import (
    CodedVideoGrainMetadataDict,
    FractionDict,
    GrainDataParameterType,
    RationalTypes)

from ..cogenums import CogFrameFormat, CogFrameLayout
from .Grain import Grain


class CodedVideoGrain(Grain):
    """\
A class representing a coded video grain.

Any grain can be freely cast to a tuple:

  (meta, data)

where meta is a dictionary containing the grain metadata, and data is the data element described below.

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
    A string containing the type of the grain, always "coded_video"

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
    The length of the data element or 0 if that is None

The CodedVideoGrain class also provides additional properies

format
    An enumerated value of type CogFrameFormat

layout
    An enumerated value of type CogFrameLayout

origin_width
    The original video width in pixels

origin_height
    The original video height in pixels

coded_width
    The coded video width in pixels

coded_height
    The coded video height in pixels

temporal_offset
    A signed integer value indicating the offset from the origin timestamp of
    this grain to the expected presentation time of the picture in frames.

unit_offsets
    A list-like object containing integer offsets of coded units within the
    data array.
"""
    def __init__(self,
                 meta: CodedVideoGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
                 src_id: Optional[UUID] = None,
                 flow_id: Optional[UUID] = None,
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
                 unit_offsets: Optional[List[int]] = None):
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
                    "grain_type": "coded_video",
                    "source_id": str(src_id),
                    "flow_id": str(flow_id),
                    "origin_timestamp": str(mediatimestamp(origin_timestamp)),
                    "sync_timestamp": str(mediatimestamp(sync_timestamp)),
                    "creation_timestamp": str(mediatimestamp(creation_timestamp)),
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

        super().__init__(meta, data)
        self.meta: CodedVideoGrainMetadataDict

        self._factory = "CodedVideoGrain"
        self.meta['grain']['grain_type'] = 'coded_video'
        if 'cog_coded_frame' not in self.meta['grain']:
            self.meta['grain']['cog_coded_frame'] = {}  # type: ignore
        if 'format' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['format'] = int(CogFrameFormat.UNKNOWN)
        if 'layout' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['layout'] = int(CogFrameLayout.UNKNOWN)
        if 'origin_width' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['origin_width'] = 0
        if 'origin_height' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['origin_height'] = 0
        if 'coded_width' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['coded_width'] = 0
        if 'coded_height' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['coded_height'] = 0
        if 'temporal_offset' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['temporal_offset'] = 0
        if 'length' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['length'] = 0
        if 'is_key_frame' not in self.meta['grain']['cog_coded_frame']:
            self.meta['grain']['cog_coded_frame']['is_key_frame'] = False
        self.meta['grain']['cog_coded_frame']['format'] = int(self.meta['grain']['cog_coded_frame']['format'])
        self.meta['grain']['cog_coded_frame']['layout'] = int(self.meta['grain']['cog_coded_frame']['layout'])

    @property
    def format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])

    @format.setter
    def format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_coded_frame']['format'] = int(value)

    @property
    def cog_frame_format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_coded_frame']['format'])

    @cog_frame_format.setter
    def cog_frame_format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_coded_frame']['format'] = int(value)

    @property
    def layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @layout.setter
    def layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_coded_frame']['layout'] = int(value)

    @property
    def cog_frame_layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @cog_frame_layout.setter
    def cog_frame_layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_coded_frame']['layout'] = int(value)

    @property
    def origin_width(self) -> int:
        return self.meta['grain']['cog_coded_frame']['origin_width']

    @origin_width.setter
    def origin_width(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['origin_width'] = value

    @property
    def origin_height(self) -> int:
        return self.meta['grain']['cog_coded_frame']['origin_height']

    @origin_height.setter
    def origin_height(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['origin_height'] = value

    @property
    def coded_width(self) -> int:
        return self.meta['grain']['cog_coded_frame']['coded_width']

    @coded_width.setter
    def coded_width(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['coded_width'] = value

    @property
    def coded_height(self) -> int:
        return self.meta['grain']['cog_coded_frame']['coded_height']

    @coded_height.setter
    def coded_height(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['coded_height'] = value

    @property
    def is_key_frame(self) -> bool:
        return self.meta['grain']['cog_coded_frame']['is_key_frame']

    @is_key_frame.setter
    def is_key_frame(self, value: bool) -> None:
        self.meta['grain']['cog_coded_frame']['is_key_frame'] = bool(value)

    @property
    def temporal_offset(self) -> int:
        return self.meta['grain']['cog_coded_frame']['temporal_offset']

    @temporal_offset.setter
    def temporal_offset(self, value: int) -> None:
        self.meta['grain']['cog_coded_frame']['temporal_offset'] = value

    @property
    def source_aspect_ratio(self) -> Optional[Fraction]:
        if 'source_aspect_ratio' in self.meta['grain']['cog_coded_frame']:
            return Fraction(cast(FractionDict,
                                 self.meta['grain']['cog_coded_frame']['source_aspect_ratio'])['numerator'],
                            cast(FractionDict,
                                 self.meta['grain']['cog_coded_frame']['source_aspect_ratio'])['denominator'])
        else:
            return None

    @source_aspect_ratio.setter
    def source_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_coded_frame']['source_aspect_ratio'] = {'numerator': value.numerator,
                                                                        'denominator': value.denominator}

    @property
    def pixel_aspect_ratio(self) -> Optional[Fraction]:
        if 'pixel_aspect_ratio' in self.meta['grain']['cog_coded_frame']:
            return Fraction(cast(FractionDict,
                                 self.meta['grain']['cog_coded_frame']['pixel_aspect_ratio'])['numerator'],
                            cast(FractionDict,
                                 self.meta['grain']['cog_coded_frame']['pixel_aspect_ratio'])['denominator'])
        else:
            return None

    @pixel_aspect_ratio.setter
    def pixel_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_coded_frame']['pixel_aspect_ratio'] = {'numerator': value.numerator,
                                                                       'denominator': value.denominator}

    class UNITOFFSETS(MutableSequence):
        def __init__(self, parent: "CodedVideoGrain"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> int: ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> List[int]: ...

        def __getitem__(self, key):  # noqa: F811
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key]
            else:
                raise IndexError("list index out of range")

        @overload
        def __setitem__(self, key: int, value: int) -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: Iterable[int]) -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'][key] = value
            else:
                raise IndexError("list assignment index out of range")

        def __delitem__(self, key: Union[int, slice]) -> None:
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                del cast(List[int], self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])[key]
                if len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets']) == 0:
                    del self.parent.meta['grain']['cog_coded_frame']['unit_offsets']
            else:
                raise IndexError("list assignment index out of range")

        def insert(self, key: int, value: int) -> None:
            if 'unit_offsets' not in self.parent.meta['grain']['cog_coded_frame']:
                d: List[int] = []
                d.insert(key, value)
                self.parent.meta['grain']['cog_coded_frame']['unit_offsets'] = d
            else:
                cast(List[int], self.parent.meta['grain']['cog_coded_frame']['unit_offsets']).insert(key, value)

        def __len__(self) -> int:
            if 'unit_offsets' in self.parent.meta['grain']['cog_coded_frame']:
                return len(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])
            else:
                return 0

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        def __repr__(self) -> str:
            if 'unit_offsets' not in self.parent.meta['grain']['cog_coded_frame']:
                return repr([])
            else:
                return repr(self.parent.meta['grain']['cog_coded_frame']['unit_offsets'])

    @property
    def unit_offsets(self) -> "CodedVideoGrain.UNITOFFSETS":
        return CodedVideoGrain.UNITOFFSETS(self)

    @unit_offsets.setter
    def unit_offsets(self, value: Iterable[int]) -> None:
        if value is not None and not (hasattr(value, "__len__") and len(cast(Sized, value)) == 0):
            self.meta['grain']['cog_coded_frame']['unit_offsets'] = list(value)
        elif 'unit_offsets' in self.meta['grain']['cog_coded_frame']:
            del self.meta['grain']['cog_coded_frame']['unit_offsets']

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.rate:
            return self.rate
        else:
            return None
