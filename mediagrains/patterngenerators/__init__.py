#
# Copyright 2020 British Broadcasting Corporation
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
This submodule contains classes which can be used to generate various test
grains in a wide variety of formats in a random access fashion.

This is intended to replace mediagrains.testsignalgenerator, which is now deprecated.
"""

from .abc import PatternGenerator, FixedRatePatternGenerator

__all__ = [
    "PatternGenerator",
    "FixedRatePatternGenerator"
]
