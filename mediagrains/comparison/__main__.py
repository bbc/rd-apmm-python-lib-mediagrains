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
"""An example of using the comparison module in practice."""
from fractions import Fraction
from uuid import uuid1

from mediatimestamp import CountRange

from . import compare_grain
from .options import Exclude
from ..patterngenerators.video import LumaSteps, ColourBars


src_id = uuid1()
flow_id = uuid1()

cr = CountRange(1, 10)

ls = LumaSteps(src_id, flow_id, 1920, 1080)
ls_itr = ls.__getitem__(cr)
a = next(ls_itr)

cb = ColourBars(src_id, flow_id, 1920, 1080)
cb_itr = cb.__getitem__(cr)
b = next(cb_itr)

a.add_timelabel('tmp', 3, Fraction(25, 1))
b.add_timelabel('tmp', 3, Fraction(25, 1))

m = compare_grain(a, b,
                  Exclude.origin_timestamp,
                  Exclude.sync_timestamp,
                  Exclude.creation_timestamp,
                  Exclude.data)
print(m)
print(m.msg)
