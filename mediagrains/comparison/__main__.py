#!/usr/bin/env python3
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

from fractions import Fraction

from . import compare_grain
from .options import Exclude


from ..testsignalgenerator import LumaSteps
from uuid import uuid1

src_id = uuid1()
flow_id = uuid1()

a = next(LumaSteps(src_id, flow_id, 1920, 1080))
b = next(LumaSteps(src_id, flow_id, 1920, 1080))

a.add_timelabel('tmp', 3, Fraction(25, 1))
b.add_timelabel('tmp', 3, Fraction(25, 1))

m = compare_grain(a, b,
                  Exclude.origin_timestamp,
                  Exclude.sync_timestamp,
                  Exclude.creation_timestamp)
print(m)
print(m.msg)
