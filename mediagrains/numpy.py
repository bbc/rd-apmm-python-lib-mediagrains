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
Numpy compatible layer for mediagrains, but only available in python 3.6+
"""

from sys import version_info

if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    from mediagrains_py36.numpy import VideoGrain, VIDEOGRAIN # noqa: F401

    __all__ = ['VideoGrain', 'VIDEOGRAIN']
else:
    __all__ = []
