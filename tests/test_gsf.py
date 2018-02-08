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
from mediagrains.grain import GRAIN, VIDEOGRAIN, AUDIOGRAIN, CODEDVIDEOGRAIN
from mediagrains import Grain, VideoGrain
from mediagrains.gsf import loads
from mediagrains.gsf import GSFDecodeError
from mediagrains.gsf import GSFDecodeBadVersionError
from mediagrains.gsf import GSFDecodeBadFileTypeError
from mediagrains.cogframe import CogFrameFormat, CogFrameLayout, CogAudioFormat
from nmoscommon.timestamp import Timestamp, TimeOffset
from fractions import Fraction
from datetime import datetime

with open('examples/video.gsf', 'rb') as f:
    VIDEO_DATA = f.read()

with open('examples/coded_video.gsf', 'rb') as f:
    CODED_VIDEO_DATA = f.read()

with open('examples/audio.gsf', 'rb') as f:
    AUDIO_DATA = f.read()


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

    def test_loads_audio(self):
        (head, segments) = loads(AUDIO_DATA)

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 37, 50))
        self.assertEqual(head['id'], UUID('781fb6c5-d22f-4df5-ba69-69059efd5ced'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('fc4c5533-3fad-4437-93c0-8668cb876578'))
        self.assertIn(head['segments'][0]['local_id'], segments)
        self.assertEqual(len(segments[head['segments'][0]['local_id']]), head['segments'][0]['count'])

        start_ots = Timestamp(1420102800, 0)
        ots = start_ots
        total_samples = 0
        for grain in segments[head['segments'][0]['local_id']]:
            self.assertIsInstance(grain, AUDIOGRAIN)
            self.assertEqual(grain.grain_type, "audio")
            self.assertEqual(grain.source_id, UUID('38bfd902-b35f-40d6-9ecf-dc95869130cf'))
            self.assertEqual(grain.flow_id, UUID('f1c8c095-5739-46f4-9bbc-3d7050c9ba23'))
            self.assertEqual(grain.origin_timestamp, ots)

            self.assertEqual(grain.format, CogAudioFormat.S24_INTERLEAVED)
            self.assertEqual(grain.channels, 2)
            self.assertEqual(grain.samples, 1024)
            self.assertEqual(grain.sample_rate, 48000)

            self.assertEqual(len(grain.data), 6144)
            total_samples += grain.samples
            ots = start_ots + TimeOffset.from_count(total_samples, grain.sample_rate)

    def test_loads_coded_video(self):
        (head, segments) = loads(CODED_VIDEO_DATA)

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 38, 41))
        self.assertEqual(head['id'], UUID('8875f02c-2528-4566-9e9a-23efc3a9bbe5'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('bdfa1343-0a20-4a98-92f5-0f7f0eb75479'))
        self.assertIn(head['segments'][0]['local_id'], segments)
        self.assertEqual(len(segments[head['segments'][0]['local_id']]), head['segments'][0]['count'])

        ots = Timestamp(1420102800, 0)
        unit_offsets = [[0, 6, 34, 42, 711, 719],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14],
                        [0, 6, 14]]
        for grain in segments[head['segments'][0]['local_id']]:
            self.assertIsInstance(grain, CODEDVIDEOGRAIN)
            self.assertEqual(grain.grain_type, "coded_video")
            self.assertEqual(grain.source_id, UUID('49578552-fb9e-4d3e-a197-3e3c437a895d'))
            self.assertEqual(grain.flow_id, UUID('b6b05efb-6067-4ff8-afac-ec735a85674e'))
            self.assertEqual(grain.origin_timestamp, ots)
            ots += TimeOffset.from_nanosec(20000000)

            self.assertEqual(grain.format, CogFrameFormat.H264)
            self.assertEqual(grain.layout, CogFrameLayout.FULL_FRAME)
            self.assertEqual(grain.origin_width, 1920)
            self.assertEqual(grain.origin_height, 1080)
            self.assertEqual(grain.coded_width, 0)
            self.assertEqual(grain.coded_height, 0)
            self.assertEqual(grain.length, 0)
            self.assertEqual(grain.temporal_offset, 0)
            self.assertEqual(grain.unit_offsets, unit_offsets[0])
            unit_offsets.pop(0)

    def test_loads_rejects_incorrect_type_file(self):
        with self.assertRaises(GSFDecodeBadFileTypeError) as cm:
            loads(b"POTATO23\x07\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.filetype, b"POTATO23")

    def test_loads_rejects_incorrect_version_file(self):
        with self.assertRaises(GSFDecodeBadVersionError) as cm:
            loads(b"SSBBgrsg\x08\x00\x03\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.major, 8)
        self.assertEqual(cm.exception.minor, 3)

