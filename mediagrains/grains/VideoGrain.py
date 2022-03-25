from collections.abc import MutableSequence, Mapping
from fractions import Fraction

from typing import (
    List,
    Union,
    Optional,
    overload,
    cast,
    Iterator,
    Iterable)
from typing_extensions import Literal
from uuid import UUID

from mediatimestamp.immutable import Timestamp, SupportsMediaTimestamp, mediatimestamp
from ..typing import (
    RationalTypes,
    VideoGrainComponentDict,
    FractionDict,
    VideoGrainMetadataDict,
    GrainDataParameterType)

from ..cogenums import CogFrameFormat, CogFrameLayout
from .Grain import Grain


class VideoGrain(Grain):
    """\
A class representing a raw video grain.

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
    A string containing the type of the grain, always "video"

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

The VideoGrain class also provides additional properies

format
    An enumerated value of type CogFrameFormat

width
    The video width in pixels

height
    The video height in pixels

layout
    An enumerated value of type CogFrameLayout

extension
    A numeric value indicating the offset from the start of the data array to
    the start of the actual data, usually 0.

source_aspect_ratio
    A fractions.Fraction object indicating the video source aspect ratio, or None

pixel_aspect_ratio
    A fractions.Fraction object indicating the video pixel aspect ratio, or None

components
    A list-like sequence of VideoGrain.COMPONENT objects
    """

    class COMPONENT(Mapping):
        """
A class representing a video component, it may be treated as a dictionary of the form:

    {"stride": <an integer>,
     "offset": <an integer>,
     "width": <an integer>,
     "height": <an integer>,
     "length": <an integer>}

with additional properties allowing access to the members:

stride
    The offset in bytes between the first data byte of each line in the data
    array and the first byte of the next.

offset
    The offset in bytes from the start of the data array to the first byte of
    the first line of the data in this component.

width
    The number of samples per line in this component

height
    The number of lines in this component

length
    The total length of the data for this component in bytes
"""
        def __init__(self, meta: VideoGrainComponentDict):
            self.meta = meta

        def __getitem__(self, key: Literal['stride', 'offset', 'width', 'height', 'length']) -> int:
            return self.meta[key]

        def __setitem__(self, key: Literal['stride', 'offset', 'width', 'height', 'length'], value: int) -> None:
            self.meta[key] = value

        def __iter__(self) -> Iterator[str]:
            return self.meta.__iter__()

        def __len__(self) -> int:
            return self.meta.__len__()

        def __eq__(self, other: object) -> bool:
            return dict(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

        @property
        def stride(self) -> int:
            return self.meta['stride']

        @stride.setter
        def stride(self, value: int) -> None:
            self.meta['stride'] = value

        @property
        def offset(self) -> int:
            return self.meta['offset']

        @offset.setter
        def offset(self, value: int) -> None:
            self.meta['offset'] = value

        @property
        def width(self) -> int:
            return self.meta['width']

        @width.setter
        def width(self, value: int) -> None:
            self.meta['width'] = value

        @property
        def height(self) -> int:
            return self.meta['height']

        @height.setter
        def height(self, value: int) -> None:
            self.meta['height'] = value

        @property
        def length(self) -> int:
            return self.meta['length']

        @length.setter
        def length(self, value: int) -> None:
            self.meta['length'] = value

    class COMPONENT_LIST(MutableSequence):
        def __init__(self, parent: "VideoGrain"):
            self.parent = parent

        @overload
        def __getitem__(self, key: int) -> "VideoGrain.COMPONENT": ...

        @overload  # noqa: F811
        def __getitem__(self, key: slice) -> "List[VideoGrain.COMPONENT]": ...

        def __getitem__(self, key):  # noqa: F811
            if isinstance(key, int):
                return type(self.parent).COMPONENT(self.parent.meta['grain']['cog_frame']['components'][key])
            else:
                return [type(self.parent).COMPONENT(
                    self.parent.meta['grain']['cog_frame']['components'][k]) for k in range(len(self))[key]]

        @overload
        def __setitem__(self, key: int, value: VideoGrainComponentDict) -> None: ...

        @overload  # noqa: F811
        def __setitem__(self, key: slice, value: Iterable[VideoGrainComponentDict]) -> None: ...

        def __setitem__(self, key, value):  # noqa: F811
            if isinstance(key, int):
                self.parent.meta['grain']['cog_frame']['components'][key] = type(self.parent).COMPONENT(value)
            else:
                values = iter(value)
                for n in range(len(self))[key]:
                    self.parent.meta['grain']['cog_frame']['components'][n] = type(self.parent).COMPONENT(next(values))

        def __delitem__(self, key: Union[int, slice]) -> None:
            del self.parent.meta['grain']['cog_frame']['components'][key]

        def insert(self, key: int, value: VideoGrainComponentDict) -> None:
            self.parent.meta['grain']['cog_frame']['components'].insert(
                key, type(self.parent).COMPONENT(value))  # type: ignore

        def __len__(self) -> int:
            return len(self.parent.meta['grain']['cog_frame']['components'])

        def __eq__(self, other: object) -> bool:
            return list(self) == other

        def __ne__(self, other: object) -> bool:
            return not (self == other)

    def __init__(self,
                 meta: VideoGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
                 src_id: Optional[UUID] = None,
                 flow_id: Optional[UUID] = None,
                 origin_timestamp: Optional[SupportsMediaTimestamp] = None,
                 creation_timestamp: Optional[SupportsMediaTimestamp] = None,
                 sync_timestamp: Optional[SupportsMediaTimestamp] = None,
                 rate: Fraction = Fraction(25, 1),
                 duration: Fraction = Fraction(1, 25),
                 cog_frame_format: CogFrameFormat = CogFrameFormat.UNKNOWN,
                 width: int = 1920,
                 height: int = 1080,
                 cog_frame_layout: CogFrameLayout = CogFrameLayout.UNKNOWN):

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
                    'grain_type': "video",
                    'source_id': str(src_id),
                    'flow_id': str(flow_id),
                    'origin_timestamp': str(mediatimestamp(origin_timestamp)),
                    'sync_timestamp': str(mediatimestamp(sync_timestamp)),
                    'creation_timestamp': str(mediatimestamp(creation_timestamp)),
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
                if fmt in (CogFrameFormat.YUYV, CogFrameFormat.UYVY, CogFrameFormat.AYUV):
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
                if fmt in (CogFrameFormat.YUYV, CogFrameFormat.UYVY, CogFrameFormat.AYUV):
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

        super().__init__(meta=meta, data=data)
        self.meta: VideoGrainMetadataDict

        self._factory = "VideoGrain"
        self.meta['grain']['grain_type'] = 'video'
        if 'cog_frame' not in self.meta['grain']:
            self.meta['grain']['cog_frame'] = {
                'format': int(CogFrameFormat.UNKNOWN),
                'width': 0,
                'height': 0,
                'layout': int(CogFrameLayout.UNKNOWN),
                'extension': 0,
                'components': []
            }
        self.meta['grain']['cog_frame']['format'] = int(self.meta['grain']['cog_frame']['format'])
        self.meta['grain']['cog_frame']['layout'] = int(self.meta['grain']['cog_frame']['layout'])
        self.components = VideoGrain.COMPONENT_LIST(self)

    @property
    def format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_frame']['format'])

    @format.setter
    def format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_frame']['format'] = int(value)

    @property
    def cog_frame_format(self) -> CogFrameFormat:
        return CogFrameFormat(self.meta['grain']['cog_frame']['format'])

    @cog_frame_format.setter
    def cog_frame_format(self, value: CogFrameFormat) -> None:
        self.meta['grain']['cog_frame']['format'] = int(value)

    @property
    def width(self) -> int:
        return self.meta['grain']['cog_frame']['width']

    @width.setter
    def width(self, value: int) -> None:
        self.meta['grain']['cog_frame']['width'] = value

    @property
    def height(self) -> int:
        return self.meta['grain']['cog_frame']['height']

    @height.setter
    def height(self, value: int) -> None:
        self.meta['grain']['cog_frame']['height'] = value

    @property
    def layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_frame']['layout'])

    @layout.setter
    def layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_frame']['layout'] = int(value)

    @property
    def cog_frame_layout(self) -> CogFrameLayout:
        return CogFrameLayout(self.meta['grain']['cog_frame']['layout'])

    @cog_frame_layout.setter
    def cog_frame_layout(self, value: CogFrameLayout) -> None:
        self.meta['grain']['cog_frame']['layout'] = int(value)

    @property
    def extension(self) -> int:
        return self.meta['grain']['cog_frame']['extension']

    @extension.setter
    def extension(self, value: int) -> None:
        self.meta['grain']['cog_frame']['extension'] = value

    @property
    def source_aspect_ratio(self) -> Optional[Fraction]:
        if 'source_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(cast(FractionDict, self.meta['grain']['cog_frame']['source_aspect_ratio'])['numerator'],
                            cast(FractionDict, self.meta['grain']['cog_frame']['source_aspect_ratio'])['denominator'])
        else:
            return None

    @source_aspect_ratio.setter
    def source_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_frame']['source_aspect_ratio'] = {'numerator': value.numerator,
                                                                  'denominator': value.denominator}

    @property
    def pixel_aspect_ratio(self) -> Optional[Fraction]:
        if 'pixel_aspect_ratio' in self.meta['grain']['cog_frame']:
            return Fraction(cast(FractionDict, self.meta['grain']['cog_frame']['pixel_aspect_ratio'])['numerator'],
                            cast(FractionDict, self.meta['grain']['cog_frame']['pixel_aspect_ratio'])['denominator'])
        else:
            return None

    @pixel_aspect_ratio.setter
    def pixel_aspect_ratio(self, value: RationalTypes) -> None:
        value = Fraction(value)
        self.meta['grain']['cog_frame']['pixel_aspect_ratio'] = {'numerator': value.numerator,
                                                                 'denominator': value.denominator}

    @property
    def expected_length(self) -> int:
        length = 0
        for component in self.components:
            if component.offset + component.length > length:
                length = component.offset + component.length
        return length

    @property
    def media_rate(self) -> Optional[Fraction]:
        if self.rate:
            return self.rate
        else:
            return None
