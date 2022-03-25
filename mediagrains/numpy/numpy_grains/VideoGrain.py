from ...cogenums import (
    CogFrameFormat,
    CogFrameLayout,
    COG_FRAME_IS_PLANAR,
    COG_FRAME_FORMAT_BYTES_PER_VALUE,
    COG_FRAME_IS_PLANAR_RGB)
import mediagrains.grains as bytesgrain
from copy import copy, deepcopy
import uuid

import numpy as np
from numpy.lib.stride_tricks import as_strided

from typing import Callable, Dict, Tuple, Optional, Awaitable, cast, Generator, Any
from ...typing import VideoGrainMetadataDict, GrainDataType, GrainDataParameterType

from inspect import isawaitable

from enum import Enum, auto
from uuid import UUID
from fractions import Fraction
from mediatimestamp.immutable import SupportsMediaTimestamp


def _dtype_from_cogframeformat(fmt: CogFrameFormat) -> np.dtype:
    """This method returns the numpy "data type" for a particular video format.

    For planar and padded formats this is the size of the native integer type that is used to handle the samples (eg.
    8bit, 16bit, etc ...) For weird packed formats like v210 (10-bit samples packed so that there are 3 10-bit samples
    in every 32-bit word) this is not possible. Instead for v210 we return uint32, since that is the most useful
    native data type that always corresponds to an integral number of samples.
    """
    if COG_FRAME_IS_PLANAR(fmt):
        if COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 1:
            return np.dtype(np.uint8)
        elif COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 2:
            return np.dtype(np.uint16)
        elif COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 4:
            return np.dtype(np.uint32)
    elif fmt in [CogFrameFormat.UYVY,
                 CogFrameFormat.YUYV,
                 CogFrameFormat.AYUV,
                 CogFrameFormat.RGB,
                 CogFrameFormat.RGBx,
                 CogFrameFormat.RGBA,
                 CogFrameFormat.BGRx,
                 CogFrameFormat.BGRx,
                 CogFrameFormat.ARGB,
                 CogFrameFormat.xRGB,
                 CogFrameFormat.ABGR,
                 CogFrameFormat.xBGR]:
        return np.dtype(np.uint8)
    elif fmt == CogFrameFormat.v216:
        return np.dtype(np.uint16)
    elif fmt == CogFrameFormat.v210:
        return np.dtype(np.uint32)

    raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


class ComponentDataList(list):
    class ComponentOrder (Enum):
        YUV = auto()
        RGB = auto()
        BGR = auto()
        X = auto()

    def __init__(self, data: list, arrangement: ComponentOrder = ComponentOrder.X):
        super().__init__(data)
        if arrangement == ComponentDataList.ComponentOrder.YUV:
            self.Y = self[0]
            self.U = self[1]
            self.V = self[2]
        elif arrangement == ComponentDataList.ComponentOrder.RGB:
            self.R = self[0]
            self.G = self[1]
            self.B = self[2]
        elif arrangement == ComponentDataList.ComponentOrder.BGR:
            self.B = self[0]
            self.G = self[1]
            self.R = self[2]


def _component_arrangement_from_format(fmt: CogFrameFormat):
    """This method returns the ordering of the components in the component data arrays that are used to represent a
    particular format.

    Note that for the likes of UYVY this will return YUV since the planes are represented in that order by the
    interface even though they are interleved in the data.

    For formats where no meaningful component access can be provided (v210, compressed formats, etc ...) the value X
    is returned.
    """
    if COG_FRAME_IS_PLANAR(fmt):
        if COG_FRAME_IS_PLANAR_RGB(fmt):
            return ComponentDataList.ComponentOrder.RGB
        else:
            return ComponentDataList.ComponentOrder.YUV
    elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.YUYV, CogFrameFormat.v216, CogFrameFormat.AYUV]:
        return ComponentDataList.ComponentOrder.YUV
    elif fmt in [
     CogFrameFormat.RGB, CogFrameFormat.RGBA, CogFrameFormat.RGBx, CogFrameFormat.ARGB, CogFrameFormat.xRGB]:
        return ComponentDataList.ComponentOrder.RGB
    elif fmt in [CogFrameFormat.BGRA, CogFrameFormat.BGRx, CogFrameFormat.xBGR, CogFrameFormat.ABGR]:
        return ComponentDataList.ComponentOrder.BGR
    else:
        return ComponentDataList.ComponentOrder.X


def _component_arrays_for_interleaved_422(
 data0: np.ndarray, data1: np.ndarray, data2: np.ndarray, width: int, height: int, stride: int, itemsize: int):
    return [
        as_strided(data0,
                   shape=(height, width),
                   strides=(stride, itemsize*2)).transpose(),
        as_strided(data1,
                   shape=(height, width//2),
                   strides=(stride, itemsize*4)).transpose(),
        as_strided(data2,
                   shape=(height, width//2),
                   strides=(stride, itemsize*4)).transpose()]


def _component_arrays_for_interleaved_444_take_three(data0: np.ndarray,
                                                     data1: np.ndarray,
                                                     data2: np.ndarray,
                                                     width: int,
                                                     height: int,
                                                     stride: int,
                                                     itemsize: int,
                                                     num_components: int = 3):
    return [
        as_strided(data0,
                   shape=(height, width),
                   strides=(stride, itemsize*num_components)).transpose(),
        as_strided(data1,
                   shape=(height, width),
                   strides=(stride, itemsize*num_components)).transpose(),
        as_strided(data2,
                   shape=(height, width),
                   strides=(stride, itemsize*num_components)).transpose()]


def _component_arrays_for_data_and_type(
 data: Optional[np.ndarray], fmt: CogFrameFormat, components: bytesgrain.VideoGrain.COMPONENT_LIST):
    """This method returns a list of numpy array views which can be used to directly access the components of the video
    frame without any need for conversion or copying. This is not possible for all formats.

    For planar formats this simply returns a list of array views of the planes.

    For interleaved formats this returns a list of array views that use stride tricks to access alternate elements in
    the source data array.

    For weird packed formats like v210 nothing can be done, an empty list is returned since no individual component
    access is possible.
    """
    if data is None:
        return []

    if COG_FRAME_IS_PLANAR(fmt):
        return [
            as_strided(data[component.offset//data.itemsize:(component.offset + component.length)//data.itemsize],
                       shape=(component.height, component.width),
                       strides=(component.stride, data.itemsize)).transpose()
            for component in components]
    elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.v216]:
        # Either 8 or 16 bits 4:2:2 interleavedd in UYVY order
        return _component_arrays_for_interleaved_422(
            data[1:], data, data[2:], components[0].width, components[0].height, components[0].stride, data.itemsize)
    elif fmt == CogFrameFormat.YUYV:
        # 8 bit 4:2:2 interleaved in YUYV order
        return _component_arrays_for_interleaved_422(
            data, data[1:], data[3:], components[0].width, components[0].height, components[0].stride, data.itemsize)
    elif fmt == CogFrameFormat.RGB:
        # 8 bit 4:4:4 three components interleaved in RGB order
        return _component_arrays_for_interleaved_444_take_three(data,
                                                                data[1:],
                                                                data[2:],
                                                                components[0].width,
                                                                components[0].height,
                                                                components[0].stride,
                                                                data.itemsize)
    elif fmt in [CogFrameFormat.RGBx,
                 CogFrameFormat.RGBA,
                 CogFrameFormat.BGRx,
                 CogFrameFormat.BGRx]:
        # 8 bit 4:4:4:4 four components interleave dropping the fourth component
        return _component_arrays_for_interleaved_444_take_three(data,
                                                                data[1:],
                                                                data[2:],
                                                                components[0].width,
                                                                components[0].height,
                                                                components[0].stride,
                                                                data.itemsize,
                                                                num_components=4)
    elif fmt in [CogFrameFormat.ARGB,
                 CogFrameFormat.xRGB,
                 CogFrameFormat.ABGR,
                 CogFrameFormat.xBGR,
                 CogFrameFormat.AYUV]:
        # 8 bit 4:4:4:4 four components interleave dropping the first component
        return _component_arrays_for_interleaved_444_take_three(data[1:],
                                                                data[2:],
                                                                data[3:],
                                                                components[0].width,
                                                                components[0].height,
                                                                components[0].stride,
                                                                data.itemsize,
                                                                num_components=4)
    elif fmt == CogFrameFormat.v210:
        # v210 is barely supported. Convert it to something else to actually use it!
        # This method returns an empty list because component access isn't supported, but
        # the more basic access to the underlying data is.
        return []

    raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


class VideoGrain (bytesgrain.VideoGrain):
    ConversionFunc = Callable[["VideoGrain", "VideoGrain"], None]

    _grain_conversions: Dict[Tuple[CogFrameFormat, CogFrameFormat], ConversionFunc] = {}

    def __init__(self,
                 *args,
                 grain: bytesgrain.VideoGrain = None,
                 meta: VideoGrainMetadataDict = None,
                 data: GrainDataParameterType = None,
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
                 flow_id: Optional[UUID] = None):
        if grain and isinstance(grain, bytesgrain.VideoGrain):
            meta = grain.meta
            data = grain.data
            super().__init__(meta, data)
        else:
            if args and len(args) == 2:
                meta = cast(VideoGrainMetadataDict, args[0])
                data = cast(GrainDataParameterType, args[1])
            super().__init__(meta=meta, data=data, origin_timestamp=origin_timestamp,
                             creation_timestamp=creation_timestamp, sync_timestamp=sync_timestamp, rate=rate,
                             duration=duration, cog_frame_format=cog_frame_format, cog_frame_layout=cog_frame_layout,
                             width=width, height=height, src_id=src_id, flow_id=flow_id)

        self._data: Optional[np.ndarray]
        self._data_fetcher_coroutine: Optional[Awaitable[GrainDataType]]
        self.component_data: ComponentDataList

        if self._data is not None:
            self._data = np.frombuffer(self._data, dtype=_dtype_from_cogframeformat(self.format))
            self.component_data = ComponentDataList(
                _component_arrays_for_data_and_type(self._data, self.format, self.components),
                arrangement=_component_arrangement_from_format(self.format))
        else:
            self.component_data = ComponentDataList([])

    @property
    def length(self) -> int:
        if self._data is None:
            return 0
        return self._data.nbytes

    @length.setter
    def length(self, L: int) -> None:
        # Get the length Property from the parent class and set the new value L
        super(VideoGrain, type(self)).length.fset(self, L)  # type: ignore

    @property
    def data(self) -> Optional[np.ndarray]:
        return self._data

    @data.setter
    def data(self, value: GrainDataParameterType):
        if isawaitable(value):
            self._data_fetcher_coroutine = cast(Awaitable[GrainDataType], value)
            self._data = None
            self.component_data = ComponentDataList([])
        else:
            self._data_fetcher_coroutine = None
            self._data = np.frombuffer(cast(bytes, value), dtype=_dtype_from_cogframeformat(self.format))
            self.component_data = ComponentDataList(
                _component_arrays_for_data_and_type(self._data, self.format, self.components),
                arrangement=_component_arrangement_from_format(self.format))

    def __array__(self) -> np.ndarray:
        return np.array(self.data)

    def __bytes__(self) -> bytes:
        if self._data is None:
            return bytes()
        return bytes(self._data)

    def __copy__(self) -> "VideoGrain":
        return VideoGrain(meta=copy(self.meta), data=self.data)

    def __deepcopy__(self, memo) -> "VideoGrain":
        return VideoGrain(meta=deepcopy(self.meta),
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

    async def __aenter__(self) -> "VideoGrain":
        await self
        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    @classmethod
    def grain_conversion(cls, fmt_in: CogFrameFormat, fmt_out: CogFrameFormat) -> Callable[
     ["VideoGrain.ConversionFunc"], "VideoGrain.ConversionFunc"]:
        """Decorator to apply to all grain conversion functions"""
        def _inner(f: "VideoGrain.ConversionFunc") -> "VideoGrain.ConversionFunc":
            cls._grain_conversions[(fmt_in, fmt_out)] = f
            return f
        return _inner

    @classmethod
    def grain_conversion_two_step(cls, fmt_in: CogFrameFormat, fmt_mid: CogFrameFormat, fmt_out: CogFrameFormat):
        """Register a grain conversion via an intermediate format, using existing conversions"""
        def _inner(grain_in: "VideoGrain", grain_out: "VideoGrain"):
            grain_mid = grain_in._similar_grain(fmt_mid)
            cls._get_grain_conversion_function(fmt_in, fmt_mid)(grain_in, grain_mid)
            cls._get_grain_conversion_function(fmt_mid, fmt_out)(grain_mid, grain_out)
        cls.grain_conversion(fmt_in, fmt_out)(_inner)

    @classmethod
    def _get_grain_conversion_function(cls, fmt_in: CogFrameFormat, fmt_out: CogFrameFormat
                                       ) -> "VideoGrain.ConversionFunc":
        """Return the registered grain conversion function for a specified type conversion, or raise
        NotImplementedError"""
        if (fmt_in, fmt_out) in cls._grain_conversions:
            return cls._grain_conversions[(fmt_in, fmt_out)]

        raise NotImplementedError("This conversion has not yet been implemented")

    def flow_id_for_converted_flow(self, fmt: CogFrameFormat) -> uuid.UUID:
        return uuid.uuid5(self.flow_id, "FORMAT_CONVERSION: {!r}".format(fmt))

    def _similar_grain(self, fmt: CogFrameFormat) -> "VideoGrain":
        """Returns a new empty grain that has the specified format, but other parameters identical to this grain."""
        return VideoGrain(src_id=self.source_id,
                          flow_id=self.flow_id_for_converted_flow(fmt),
                          origin_timestamp=self.origin_timestamp,
                          sync_timestamp=self.sync_timestamp,
                          cog_frame_format=fmt,
                          width=self.width,
                          height=self.height,
                          rate=self.rate,
                          duration=self.duration,
                          cog_frame_layout=self.layout)

    def convert(self, fmt: CogFrameFormat) -> "VideoGrain":
        """Used to convert this grain to a different cog format. Always produces a new grain.

        :param fmt: The format to convert to
        :returns: A new grain of the specified format. Notably converting to the same format is the same as a deepcopy
        :raises: NotImplementedError if the requested conversion is not possible
        """
        if self.format == fmt:
            return deepcopy(self)
        else:
            grain_out = self._similar_grain(fmt)
            self.__class__._get_grain_conversion_function(self.format, fmt)(self, grain_out)
            return grain_out

    def asformat(self, fmt: CogFrameFormat) -> "VideoGrain":
        """Used to ensure that this grain is in a particular format. Converts it if not.

        :param fmt: The format to ensure
        :returns: self or a new grain.
        :raises NotImplementedError if the requested conversion is not possible.
        """
        if self.format == fmt:
            return self
        else:
            return self.convert(fmt)
