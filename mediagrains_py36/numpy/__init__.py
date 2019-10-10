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
    COG_FRAME_FORMAT_BYTES_PER_VALUE)
from mediagrains import grain as bytesgrain
from mediagrains import grain_constructors as bytesgrain_constructors
from copy import copy, deepcopy

import numpy as np
from numpy.lib.stride_tricks import as_strided


__all__ = ['VideoGrain', 'VIDEOGRAIN']


def _dtype_from_cogframeformat(fmt: CogFrameFormat) -> np.dtype:
    if not COG_FRAME_IS_PACKED(fmt) and not COG_FRAME_IS_COMPRESSED(fmt):
        if COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 1:
            return np.dtype(np.uint8)
        elif COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 2:
            return np.dtype(np.int16)
        elif COG_FRAME_FORMAT_BYTES_PER_VALUE(fmt) == 4:
            return np.dtype(np.int32)
    elif fmt in [CogFrameFormat.UYVY,
                 CogFrameFormat.YUYV,
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
        return np.dtype(np.int16)
    elif fmt == CogFrameFormat.v210:
        return np.dtype(np.int32)

    raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


def _component_arrays_for_data_and_type(data: np.ndarray, fmt: CogFrameFormat, components: bytesgrain.VIDEOGRAIN.COMPONENT_LIST):
    if not COG_FRAME_IS_PACKED(fmt) and not COG_FRAME_IS_COMPRESSED(fmt):
        arrays = []
        for component in components:
            component_data = data[component.offset//data.itemsize:(component.offset + component.length)//data.itemsize]
            component_data = as_strided(component_data, shape=(component.height, component.width), strides=(component.stride, component_data.itemsize))
            arrays.append(component_data.transpose())
        return arrays
    elif fmt in [CogFrameFormat.UYVY, CogFrameFormat.v216]:
        return [
            as_strided(data[1:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*2)).transpose(),
            as_strided(data,
                       shape=(components[0].height, components[0].width//2),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[2:],
                       shape=(components[0].height, components[0].width//2),
                       strides=(components[0].stride, data.itemsize*4)).transpose()]
    elif fmt == CogFrameFormat.YUYV:
        return [
            as_strided(data,
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*2)).transpose(),
            as_strided(data[1:],
                       shape=(components[0].height, components[0].width//2),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[3:],
                       shape=(components[0].height, components[0].width//2),
                       strides=(components[0].stride, data.itemsize*4)).transpose()]
    elif fmt == CogFrameFormat.RGB:
        return [
            as_strided(data,
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*3)).transpose(),
            as_strided(data[1:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*3)).transpose(),
            as_strided(data[2:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*3)).transpose()]
    elif fmt in [CogFrameFormat.RGBx,
                 CogFrameFormat.RGBA,
                 CogFrameFormat.BGRx,
                 CogFrameFormat.BGRx]:
        return [
            as_strided(data,
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[1:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[2:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose()]
    elif fmt in [CogFrameFormat.ARGB,
                 CogFrameFormat.xRGB,
                 CogFrameFormat.ABGR,
                 CogFrameFormat.xBGR]:
        return [
            as_strided(data[1:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[2:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose(),
            as_strided(data[3:],
                       shape=(components[0].height, components[0].width),
                       strides=(components[0].stride, data.itemsize*4)).transpose()]
    elif fmt == CogFrameFormat.v210:
        # v210 is barely supported. Convert it to something else to actually use it!
        return []

    raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


class VIDEOGRAIN (bytesgrain.VIDEOGRAIN):
    def __init__(self, meta, data):
        super().__init__(meta, data)
        self._data = np.frombuffer(self._data, dtype=_dtype_from_cogframeformat(self.format))
        self.component_data = _component_arrays_for_data_and_type(self._data, self.format, self.components)

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


def VideoGrain(*args, **kwargs) -> VIDEOGRAIN:
    """If the first argument is a mediagrains.VIDEOGRAIN then return a mediagrains.numpy.VIDEOGRAIN representing the same data.

    Otherwise takes the same parameters as mediagrains.VideoGrain and returns the same grain converted into a mediagrains.numpy.VIDEOGRAIN
    """
    if len(args) == 1 and isinstance(args[0], bytesgrain.VIDEOGRAIN):
        rawgrain = args[0]
    else:
        rawgrain = bytesgrain_constructors.VideoGrain(*args, **kwargs)

    return VIDEOGRAIN(rawgrain.meta, rawgrain.data)
