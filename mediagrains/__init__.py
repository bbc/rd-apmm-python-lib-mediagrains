#
# Copyright 2018 British Broadcasting Corporation
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
Library for handling media grains in pure python.

The library contains the functions: Grain, VideoGrain, CodedVideoGrain,
AudioGrain, CodedAudioGrain, and EventGrain as well as the module gsf.

The individual functions document their useage.

The classes returned from the functions are fully useable as if they were a
tuple:

(meta, data)

where "meta" is a dictionary containing grain metadata in a standard format,
and "data" is a bytes-like object. When the various constructor functions
are used in a way that constructs a new data element they will construct a
bytearray object of the apropriate size. Remember that in Python 2 bytes-like
objects are stringlike, but in Python 3 they resemble sequences of integers.

Notably this means that the data element of these grains is fully compatible
with numpy and similar libraries.

The gsf and grain submodules have their own documentation.
"""

from .grain_constructors import Grain, VideoGrain, CodedVideoGrain, AudioGrain, CodedAudioGrain, EventGrain
from .typing import ParseGrainType

__all__ = ["Grain", "VideoGrain", "CodedVideoGrain", "AudioGrain", "CodedAudioGrain", "EventGrain", "ParseGrainType"]
