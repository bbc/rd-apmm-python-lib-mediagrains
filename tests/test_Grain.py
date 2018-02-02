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
from __future__ import print_function
from unittest import TestCase
import uuid
from mediagrains.Grain import Grain
from nmoscommon.timestamp import Timestamp
import mock
from fractions import Fraction

class TestGrain (TestCase):
    def test_empty_grain_creation(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, cts)
        self.assertEqual(grain.sync_timestamp, cts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0,1))
        self.assertEqual(grain.duration, Fraction(0,1))
        self.assertEqual(grain.timelabels, [])

    def test_empty_grain_creation_with_ots(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.sync_timestamp, ots)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0,1))
        self.assertEqual(grain.duration, Fraction(0,1))
        self.assertEqual(grain.timelabels, [])

    def test_empty_grain_creation_with_ots_and_sts(self):
        src_id = uuid.UUID("f18ee944-0841-11e8-b0b0-17cef04bd429")
        flow_id = uuid.UUID("f79ce4da-0841-11e8-9a5b-dfedb11bafeb")
        cts = Timestamp.from_tai_sec_nsec("417798915:0")
        ots = Timestamp.from_tai_sec_nsec("417798915:5")
        sts = Timestamp.from_tai_sec_nsec("417798915:10")

        with mock.patch.object(Timestamp, "get_time", return_value=cts):
            grain = Grain(src_id, flow_id, origin_timestamp=ots, sync_timestamp=sts)

        self.assertEqual(grain.grain_type, "empty")
        self.assertEqual(grain.source_id, src_id)
        self.assertEqual(grain.flow_id, flow_id)
        self.assertEqual(grain.origin_timestamp, ots)
        self.assertEqual(grain.sync_timestamp, sts)
        self.assertEqual(grain.creation_timestamp, cts)
        self.assertEqual(grain.rate, Fraction(0,1))
        self.assertEqual(grain.duration, Fraction(0,1))
        self.assertEqual(grain.timelabels, [])
