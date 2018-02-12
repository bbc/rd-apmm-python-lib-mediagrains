#!/usr/bin/python
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

"""\
Library for handling media grains in pure python.

The library contains two functions: Grain and VideoGrain
which allow the construction of grains and video grains specifically.

If Grain is fed the deserialised json from a Video grain it will generate
a VideoGrain class, rather than a generic grain.

All the grain classes can be freely treated as 2-tuples:

(meta, data)

but can also be accessed using a number of additional convenience methods.


If used to create a new videograin the VideoGrain function will allocate an
apropriately sized bytearray to use as the data member. When initialised with
a preexisting data object anything which follows the python buffer interface
should work.

Notably this means that the data element of these grains is fully compatible
with numpy and similar libraries.
"""

from __future__ import absolute_import
from .grain import Grain, VideoGrain, CodedVideoGrain, AudioGrain, CodedAudioGrain

__all__ = ["Grain", "VideoGrain", "CodedVideoGrain", "AudioGrain", "CodedAudioGrain"]
