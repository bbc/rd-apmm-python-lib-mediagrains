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

from ..cogenums import (
    CogFrameFormat,
    CogFrameLayout)
import mediagrains.grains as bytesgrain
from typing import Optional, TypeAlias, cast
from ..typing import VideoGrainMetadataDict, GrainDataParameterType
from uuid import UUID
from fractions import Fraction
from mediatimestamp.immutable import SupportsMediaTimestamp
from .numpy_grains import VideoGrain as npVideoGrain
from .numpy_grains.VideoGrain import _dtype_from_cogframeformat
from deprecated import deprecated

__all__ = ['VideoGrain', 'VIDEOGRAIN', '_dtype_from_cogframeformat']


@deprecated(version="3.2.0", reason='A new, more Pythonic way of instantiating grains has been introduced. '
            'Please import`mediagrains.numpy.numpy_grains`.')
def VideoGrain(*args,
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
               source_id: Optional[UUID] = None,
               format: Optional[CogFrameFormat] = None,
               layout: Optional[CogFrameLayout] = None,
               flow_id: Optional[UUID] = None,
               data: GrainDataParameterType = None,
               meta: VideoGrainMetadataDict = None):
    if len(args) == 1 and isinstance(args[0], bytesgrain.VideoGrain):
        return npVideoGrain(grain=args[0])

    if format:
        cog_frame_format = format
    if layout:
        cog_frame_layout = layout
    if source_id:
        src_id = source_id

    if args:
        if isinstance(args[0], dict):
            meta = cast(VideoGrainMetadataDict, args[0])
        else:
            src_id = args[0]
        if isinstance(args[1], UUID):
            flow_id = args[1]
        else:
            data = args[1]

    return npVideoGrain(grain=None,
                        origin_timestamp=origin_timestamp,
                        creation_timestamp=creation_timestamp,
                        sync_timestamp=sync_timestamp,
                        rate=rate,
                        duration=duration,
                        cog_frame_format=cog_frame_format,
                        width=width,
                        height=height,
                        cog_frame_layout=cog_frame_layout,
                        src_id=src_id,
                        flow_id=flow_id,
                        data=data,
                        meta=meta)


VIDEOGRAIN: TypeAlias = npVideoGrain
