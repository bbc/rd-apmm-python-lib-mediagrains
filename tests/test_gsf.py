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
from uuid import UUID
from mediagrains.grain import GRAIN, VIDEOGRAIN
from mediagrains import Grain, VideoGrain
from mediagrains.gsf import loads, GSFDecodeError
from mediagrains.cogframe import CogFrameFormat, CogFrameLayout
from nmoscommon.timestamp import Timestamp, TimeOffset
from fractions import Fraction
from datetime import datetime

with open('examples/video.gsf', 'rb') as f:
    VIDEO_DATA = f.read()

class TestGSFLoads(TestCase):
    def test_loads_video(self):
        (head, segments) = loads(VIDEO_DATA)

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 38, 22))
        self.assertEqual(head['id'], UUID('163fd9b7-bef4-4d92-8488-31f3819be008'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('c6a3d3ff-74c0-446d-b59e-de1041f27e8a'))
        self.assertIn(head['segments'][0]['local_id'], segments)
        self.assertEqual(len(segments[head['segments'][0]['local_id']]), head['segments'][0]['count'])

        ots = Timestamp(1420102800, 0)
        for grain in segments[head['segments'][0]['local_id']]:
            self.assertIsInstance(grain, VIDEOGRAIN)
            self.assertEqual(grain.grain_type, "video")
            self.assertEqual(grain.source_id, UUID('49578552-fb9e-4d3e-a197-3e3c437a895d'))
            self.assertEqual(grain.flow_id, UUID('6e55f251-f75a-4d56-b3af-edb8b7993c3c'))
            self.assertEqual(grain.origin_timestamp, ots)
            ots += TimeOffset.from_nanosec(20000000)

            self.assertEqual(grain.format, CogFrameFormat.U8_420)
            self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
            self.assertEqual(grain.width, 480)
            self.assertEqual(grain.height, 270)

            self.assertEqual(len(grain.components), 3)

            self.assertEqual(grain.components[0].width, 480)
            self.assertEqual(grain.components[0].height, 270)
            self.assertEqual(grain.components[0].stride, 480)
            self.assertEqual(grain.components[0].length, 480*270)

            self.assertEqual(grain.components[1].width, 240)
            self.assertEqual(grain.components[1].height, 135)
            self.assertEqual(grain.components[1].stride, 240)
            self.assertEqual(grain.components[1].length, 240*135)

            self.assertEqual(grain.components[2].width, 240)
            self.assertEqual(grain.components[2].height, 135)
            self.assertEqual(grain.components[2].stride, 240)
            self.assertEqual(grain.components[2].length, 240*135)

            self.assertEqual(len(grain.data), grain.components[0].length + grain.components[1].length + grain.components[2].length)

    def test_loads_rejects_incorrect_version_file(self):
        with self.assertRaises(GSFDecodeError):
            loads(b"SSBBgrsg\x08\x00\x03\x00")

