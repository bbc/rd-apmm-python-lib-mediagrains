#!/usr/bin/python
#
# Copyright 2019 British Broadcasting Corporation
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
Library for handling mediagrains in numpy arrays
"""

from mediagrains.cogenums import (
    CogFrameFormat,
    COG_FRAME_IS_PACKED,
    COG_FRAME_IS_COMPRESSED,
    COG_FRAME_IS_PLANAR,
    COG_FRAME_FORMAT_BYTES_PER_VALUE,
    COG_FRAME_IS_PLANAR_RGB)
from mediagrains import grain as bytesgrain
from mediagrains import grain_constructors as bytesgrain_constructors
from copy import copy, deepcopy

import numpy as np
from numpy.lib.stride_tricks import as_strided

from typing import Callable

from enum import Enum, auto


__all__ = ['VideoGrain', 'VIDEOGRAIN']


def _dtype_from_cogframeformat(fmt: CogFrameFormat) -> np.dtype:
    """This method returns the numpy "data type" for a particular video format.

    For planar and padded formats this is the size of the native integer type that is used to handle the samples (eg. 8bit, 16bit, etc ...)
    For weird packed formats like v210 (10-bit samples packed so that there are 3 10-bit samples in every 32-bit word) this is not possible.
    Instead for v210 we return int32, since that is the most useful native data type that always corresponds to an integral number of samples.
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
        X   = auto()

    def __init__(self, data: list, arrangement: ComponentOrder=ComponentOrder.X):
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
    """This method returns the ordering of the components in the component data arrays that are used to represent a particular format.

    Note that for the likes of UYVY this will return YUV since the planes are represented in that order by the interface even though they
    are interleved in the data.

    For formats where no meaningful component access can be provided (v210, compressed formats, etc ...) the value X is returned.
    """
    if COG_FRAME_IS_PLANAR(fmt):
        if COG_FRAME_IS_PLANAR_RGB(fmt):
            return ComponentDataList.ComponentOrder.RGB
        else:
            return ComponentDataList.ComponentOrder.YUV
    elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.YUYV, CogFrameFormat.v216, CogFrameFormat.AYUV]:
        return ComponentDataList.ComponentOrder.YUV
    elif fmt in [CogFrameFormat.RGB, CogFrameFormat.RGBA, CogFrameFormat.RGBx, CogFrameFormat.ARGB, CogFrameFormat.xRGB]:
        return ComponentDataList.ComponentOrder.RGB
    elif fmt in [CogFrameFormat.BGRA, CogFrameFormat.BGRx, CogFrameFormat.xBGR, CogFrameFormat.ABGR]:
        return ComponentDataList.ComponentOrder.BGR
    else:
        return ComponentDataList.ComponentOrder.X


def _component_arrays_for_interleaved_422(data0: np.ndarray, data1: np.ndarray, data2: np.ndarray, width: int, height: int, stride: int, itemsize: int):
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


def _component_arrays_for_interleaved_444_take_three(data0: np.ndarray, data1: np.ndarray, data2: np.ndarray, width: int, height: int, stride: int, itemsize: int, num_components: int = 3):
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


def _component_arrays_for_data_and_type(data: np.ndarray, fmt: CogFrameFormat, components: bytesgrain.VIDEOGRAIN.COMPONENT_LIST):
    """This method returns a list of numpy array views which can be used to directly access the components of the video frame
    without any need for conversion or copying. This is not possible for all formats.

    For planar formats this simply returns a list of array views of the planes.

    For interleaved formats this returns a list of array views that use stride tricks to access alternate elements in the source data array.

    For weird packed formats like v210 nothing can be done, an empty list is returned since no individual component access is possible.
    """
    if COG_FRAME_IS_PLANAR(fmt):
        return [
            as_strided(data[component.offset//data.itemsize:(component.offset + component.length)//data.itemsize],
                       shape=(component.height, component.width),
                       strides=(component.stride, data.itemsize)).transpose()
            for component in components]
    elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.v216]:
        # Either 8 or 16 bits 4:2:2 interleavedd in UYVY order
        return _component_arrays_for_interleaved_422(data[1:], data, data[2:], components[0].width, components[0].height, components[0].stride, data.itemsize)
    elif fmt == CogFrameFormat.YUYV:
        # 8 bit 4:2:2 interleaved in YUYV order
        return _component_arrays_for_interleaved_422(data, data[1:], data[3:], components[0].width, components[0].height, components[0].stride, data.itemsize)
    elif fmt == CogFrameFormat.RGB:
        # 8 bit 4:4:4 three components interleaved in RGB order
        return _component_arrays_for_interleaved_444_take_three(data, data[1:], data[2:], components[0].width, components[0].height, components[0].stride, data.itemsize)
    elif fmt in [CogFrameFormat.RGBx,
                 CogFrameFormat.RGBA,
                 CogFrameFormat.BGRx,
                 CogFrameFormat.BGRx]:
        # 8 bit 4:4:4:4 four components interleave dropping the fourth component
        return _component_arrays_for_interleaved_444_take_three(data, data[1:], data[2:], components[0].width, components[0].height, components[0].stride, data.itemsize, num_components=4)
    elif fmt in [CogFrameFormat.ARGB,
                 CogFrameFormat.xRGB,
                 CogFrameFormat.ABGR,
                 CogFrameFormat.xBGR,
                 CogFrameFormat.AYUV]:
        # 8 bit 4:4:4:4 four components interleave dropping the first component
        return _component_arrays_for_interleaved_444_take_three(data[1:], data[2:], data[3:], components[0].width, components[0].height, components[0].stride, data.itemsize, num_components=4)
    elif fmt == CogFrameFormat.v210:
        # v210 is barely supported. Convert it to something else to actually use it!
        # This method returns an empty list because component access isn't supported, but
        # the more basic access to the underlying data is.
        return []

    raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


class VIDEOGRAIN (bytesgrain.VIDEOGRAIN):
    _grain_conversions = {}

    def __init__(self, meta, data):
        super().__init__(meta, data)
        self._data = np.frombuffer(self._data, dtype=_dtype_from_cogframeformat(self.format))
        self.component_data = ComponentDataList(
            _component_arrays_for_data_and_type(self._data, self.format, self.components),
            arrangement=_component_arrangement_from_format(self.format))

    def __array__(self):
        return np.array(self.data)

    def __bytes__(self):
        return bytes(self.data)

    def __copy__(self):
        return VideoGrain(copy(self.meta), self.data)

    def __deepcopy__(self, memo):
        return VideoGrain(deepcopy(self.meta), self.data.copy())

    def __repr__(self):
        if self.data is None:
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< numpy data of length {} >)".format(self._factory, self.meta, len(self.data))

    @classmethod
    def grain_conversion(cls, fmt_in: CogFrameFormat, fmt_out: CogFrameFormat):
        """Decorator to apply to all grain conversion functions"""
        def _inner(f: Callable[[cls], cls]) -> None:
            cls._grain_conversions[(fmt_in, fmt_out)] = f
            return f
        return _inner

    @classmethod
    def _get_grain_conversion_function(cls, fmt_in: CogFrameFormat, fmt_out: CogFrameFormat) -> Callable[["VIDEOGRAIN"], "VIDEOGRAIN"]:
        """Return the registered grain conversion function for a specified type conversion, or raise NotImplementedError"""
        if (fmt_in, fmt_out) in cls._grain_conversions:
            return cls._grain_conversions[(fmt_in, fmt_out)]

        raise NotImplementedError("This conversion has not yet been implemented")

    def convert(self, fmt: CogFrameFormat) -> "VIDEOGRAIN":
        """Used to convert this grain to a different cog format.

        :param fmt: The format to convert to
        :returns: A new grain of the specified format. Notably converting to the same format is the same as a deepcopy
        :raises: NotImplementedError if the requested conversion is not possible
        """
        if self.format == fmt:
            return deepcopy(self)
        else:
            return self.__class__._get_grain_conversion_function(self.format, fmt)(self)


def VideoGrain(*args, **kwargs) -> VIDEOGRAIN:
    """If the first argument is a mediagrains.VIDEOGRAIN then return a mediagrains.numpy.VIDEOGRAIN representing the same data.

    Otherwise takes the same parameters as mediagrains.VideoGrain and returns the same grain converted into a mediagrains.numpy.VIDEOGRAIN
    """
    if len(args) == 1 and isinstance(args[0], bytesgrain.VIDEOGRAIN):
        rawgrain = args[0]
    else:
        rawgrain = bytesgrain_constructors.VideoGrain(*args, **kwargs)

    return VIDEOGRAIN(rawgrain.meta, rawgrain.data)