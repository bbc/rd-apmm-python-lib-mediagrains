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

from mediagrains.cogenums import CogFrameFormat, CogFrameLayout
from mediagrains import grain as bytesgrain
from mediagrains import grain_constructors as bytesgrain_constructors
from mediatimestamp.immutable import Timestamp
from fractions import Fraction
from uuid import UUID
from copy import copy, deepcopy

import numpy as np

from typing import Union, Optional, SupportsBytes


__all__ = ['VideoGrain', 'VIDEOGRAIN']


def _dtype_from_cogframeformat(fmt: CogFrameFormat) -> np.dtype:
    if fmt in [CogFrameFormat.U8_444,
               CogFrameFormat.U8_422,
               CogFrameFormat.U8_420,
               CogFrameFormat.ALPHA_U8,
               CogFrameFormat.YUYV,
               CogFrameFormat.UYVY,
               CogFrameFormat.AYUV,
               CogFrameFormat.RGB,
               CogFrameFormat.RGBx,
               CogFrameFormat.xRGB,
               CogFrameFormat.BGRx,
               CogFrameFormat.xBGR,
               CogFrameFormat.RGBA,
               CogFrameFormat.ARGB,
               CogFrameFormat.BGRA,
               CogFrameFormat.ABGR]:
        return np.dtype(np.uint8)
    elif fmt in [CogFrameFormat.S16_444_10BIT,
                 CogFrameFormat.S16_422_10BIT,
                 CogFrameFormat.S16_420_10BIT,
                 CogFrameFormat.ALPHA_S16_10BIT,
                 CogFrameFormat.S16_444_12BIT,
                 CogFrameFormat.S16_422_12BIT,
                 CogFrameFormat.S16_420_12BIT,
                 CogFrameFormat.ALPHA_S16_12BIT,
                 CogFrameFormat.S16_444,
                 CogFrameFormat.S16_422,
                 CogFrameFormat.S16_420,
                 CogFrameFormat.ALPHA_S16]:
        return np.dtype(np.int16)
    elif fmt in [CogFrameFormat.S32_444,
                 CogFrameFormat.S32_422,
                 CogFrameFormat.S32_420,
                 CogFrameFormat.ALPHA_S32,
                 CogFrameFormat.v210]:
        return np.dtype(np.int32)
    else:
        raise NotImplementedError("Cog Frame Format not amongst those supported for numpy array interpretation")


class VIDEOGRAIN (bytesgrain.VIDEOGRAIN):
    def __init__(self, meta, data):
        super().__init__(meta, data)
        self._data = np.frombuffer(self._data, dtype=_dtype_from_cogframeformat(self.format))

    def __copy__(self):
        return VideoGrain(copy(self.meta), self.data)

    def __deepcopy__(self, memo):
        return VideoGrain(deepcopy(self.meta), self.data.copy())

    def __repr__(self):
        if self.data is None:
            return "{}({!r})".format(self._factory, self.meta)
        else:
            return "{}({!r},< numpy data of length {} >)".format(self._factory, self.meta, len(self.data))

    class COMPONENT (bytesgrain.VIDEOGRAIN.COMPONENT):
        def __init__(self, parent, index, meta):
            super().__init__(parent, index, meta)
            self.data = self.parent.parent.data[self.offset//self.parent.parent.data.itemsize:(self.offset + self.length)//self.parent.parent.data.itemsize]
            if self.parent.parent.format != CogFrameFormat.v210:
                self.data.shape = (self.height, self.width)
                # It's nicer to list width, then height
                self.data = self.data.transpose()


def VideoGrain(*args, **kwargs) -> VIDEOGRAIN:
    """If the first argument is a mediagrains.VIDEOGRAIN then return a mediagrains.numpy.VIDEOGRAIN representing the same data.

    Otherwise takes the same parameters as mediagrains.VideoGrain and returns the same grain converted into a mediagrains.numpy.VIDEOGRAIN
    """
    if len(args) == 1 and isinstance(args[0], bytesgrain.VIDEOGRAIN):
        rawgrain = args[0]
    else:
        rawgrain = bytesgrain_constructors.VideoGrain(*args, **kwargs)

    return VIDEOGRAIN(rawgrain.meta, rawgrain.data)
