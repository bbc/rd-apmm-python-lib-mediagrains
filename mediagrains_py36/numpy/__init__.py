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

import numpy as np

from typing import Union, Optional, SupportsBytes


__all__ = ['VideoGrain', 'VIDEOGRAIN']


class VIDEOGRAIN (bytesgrain.VIDEOGRAIN):
    pass


def VideoGrain(
    src_id_or_meta: Optional[Union[UUID, dict]]=None,
    flow_id_or_data: Optional[Union[UUID, SupportsBytes]]=None,
    creation_timestamp: Optional[Timestamp]=None,
    origin_timestamp: Optional[Timestamp]=None,
    sync_timestamp: Optional[Timestamp]=None,
    rate: Fraction=Fraction(25, 1),
    duration: Fraction=Fraction(1, 25),
    cog_frame_format: CogFrameLayout=CogFrameFormat.UNKNOWN,
    width: int=1920,
    height: int=1080,
    cog_frame_layout: CogFrameLayout=CogFrameLayout.UNKNOWN,
    src_id: Optional[UUID]=None,
    source_id: Optional[UUID]=None,
    format: Optional[CogFrameFormat]=None,
    layout: Optional[CogFrameLayout]=None,
    flow_id: Optional[UUID]=None,
    data: Optional[SupportsBytes]=None) -> VIDEOGRAIN:
    """\
Function called to construct a video grain either from existing data or with new data.

First method of calling:

    VideoGrain(meta, data)

where meta is a dictionary containing the grain metadata, and data is a bytes-like
object which contains the grain's payload.

A properly formated metadata dictionary for a Video Grain should look like:

        {
            "@_ns": "urn:x-ipstudio:ns:0.1",
            "grain": {
                "grain_type": "audio",
                "source_id": src_id, # str or uuid.UUID
                "flow_id": flow_id, # str or uuid.UUID
                "origin_timestamp": origin_timestamp, # str or mediatimestamps.Timestamp
                "sync_timestamp": sync_timestamp, # str or mediatimestamps.Timestamp
                "creation_timestamp": creation_timestamp, # str or mediatimestamps.Timestamp
                "rate": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "duration": {
                    "numerator": 0, # int
                    "denominator": 1, # int
                },
                "cog_frame": {
                    "format": cog_frame_format, # int or CogFrameFormat
                    "width": width, # int
                    "height": height, # int
                    "layout": cog_frame_layout, # int of CogFrameLayout
                    "extension": 0, # int
                    "components": [
                        {
                            "stride": luma_stride, # int
                            "width": luma_width, # int
                            "height": luma_height, # int
                            "length": luma_length # int
                        },
                        {
                            "stride": chroma_stride, # int
                            "width": chroma_width, # int
                            "height": chroma_height, # int
                            "length": chroma_length # int
                        },
                        {
                            "stride": chroma_stride, # int
                            "width": chroma_width, # int
                            "height": chroma_height, # int
                            "length": chroma_length # int
                        },
                    ]
                }
            }
        }

Alternatively it may be called as:

    VideoGrain(src_id, flow_id,
               origin_timestamp=None,
               sync_timestamp=None,
               rate=Fraction(25, 1),
               duration=Fraction(1, 25),
               cog_frame_format=CogFrameFormat.UNKNOWN,
               width=1920,
               height=1080,
               cog_frame_layout=CogFrameLayout.UNKNOWN,
               data=None):

in which case a new grain will be constructed with type "video" and the
specified metadata. If the data argument is None then a new bytearray object
will be constructed with size determined by the format, height, and width.
The components array will similarly be filled out automatically with correct
data for the format and size specified.


In either case the value returned by this function will be an instance of the
class mediagrains.grain.VIDEOGRAIN, and the data element stored within it will be an
instance of the class numpy.ndarray.

(the parameters "source_id" and "src_id" are aliases for each other. source_id is probably prefered,
but src_id is kept avaialble for backwards compatibility)
"""
    pass
