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
from ..typing import (
    CodedVideoGrainMetadataDict,
    GrainDataParameterType)

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
    def __init__(self, meta: CodedVideoGrainMetadataDict, data: GrainDataParameterType):
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
    def layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_coded_frame']['layout'])

    @layout.setter
    def layout(self, value: CogFrameLayout) -> None:
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
