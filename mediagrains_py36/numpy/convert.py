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
Library for converting video grain formats represented as numpy arrays.
"""

from mediagrains.cogenums import CogFrameFormat
from typing import Callable

__all__ = ["get_grain_conversion_function"]


grain_conversions = {}


def grain_conversion(fmt_in: CogFrameFormat, fmt_out: CogFrameFormat):
    def _inner(f: Callable[['VideoGrain'], 'VideoGrain']) -> None:
        global grain_conversions
        grain_conversions[(fmt_in, fmt_out)] = f
    return _inner


def get_grain_conversion_function(fmt_in: CogFrameFormat, fmt_out: CogFrameFormat) -> Callable[["VideoGrain"], "VideoGrain"]:
    if (fmt_in, fmt_out) in grain_conversions:
        return grain_conversions[(fmt_in, fmt_out)]

    raise NotImplementedError("This conversion has not yet been implemented")