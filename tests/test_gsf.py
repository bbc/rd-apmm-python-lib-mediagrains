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
from mediagrains import Grain, VideoGrain, AudioGrain, CodedVideoGrain, CodedAudioGrain, EventGrain
from mediagrains.grain import VIDEOGRAIN, AUDIOGRAIN, CODEDVIDEOGRAIN, CODEDAUDIOGRAIN, EVENTGRAIN
from mediagrains.gsf import loads, load, dumps, GSFEncoder
from mediagrains.gsf import GSFDecodeError
from mediagrains.gsf import GSFEncodeError
from mediagrains.gsf import GSFDecodeBadVersionError
from mediagrains.gsf import GSFDecodeBadFileTypeError
from mediagrains.gsf import GSFEncodeAddToActiveDump
from mediagrains.cogframe import CogFrameFormat, CogFrameLayout, CogAudioFormat
from nmoscommon.timestamp import Timestamp, TimeOffset
from datetime import datetime
from fractions import Fraction
from six import PY2, BytesIO
from frozendict import frozendict

if PY2:
    import mock
else:
    from unittest import mock

with open('examples/video.gsf', 'rb') as f:
    VIDEO_DATA = f.read()

with open('examples/coded_video.gsf', 'rb') as f:
    CODED_VIDEO_DATA = f.read()

with open('examples/audio.gsf', 'rb') as f:
    AUDIO_DATA = f.read()

with open('examples/coded_audio.gsf', 'rb') as f:
    CODED_AUDIO_DATA = f.read()

with open('examples/event.gsf', 'rb') as f:
    EVENT_DATA = f.read()


class TestGSFDumps(TestCase):
    def test_dumps_no_grains(self):
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'), UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([], tags=[('potato', 'harvest')], segment_tags=[('upside', 'down')]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(head['tags'], [('potato','harvest')])
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 0)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertNotIn(head['segments'][0]['id'], [head['id']])
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(head['segments'][0]['tags'], [('upside', 'down')])

        if len(segments) > 0:
            self.assertEqual(len(segments), 1)
            self.assertIn(1, segments)
            self.assertEqual(len(segments[1]), 0)

    def test_dumps_videograin(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        for i in range(0,len(grain.data)):
            grain.data[i] = i & 0xFF
        grain.source_aspect_ratio = Fraction(16, 9)
        grain.pixel_aspect_ratio = 1
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 1)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'video')
        self.assertEqual(segments[1][0].format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(segments[1][0].width, 1920)
        self.assertEqual(segments[1][0].height, 1080)
        self.assertEqual(segments[1][0].source_aspect_ratio, Fraction(16, 9))
        self.assertEqual(segments[1][0].pixel_aspect_ratio, Fraction(1, 1))

        self.assertEqual(segments[1][0].data, grain.data)

    def test_dumps_videograins(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        grain1 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        for i in range(0,len(grain0.data)):
            grain0.data[i] = i & 0xFF
        for i in range(0,len(grain1.data)):
            grain1.data[i] = 0xFF - (i & 0xFF)
        grain0.source_aspect_ratio = Fraction(16, 9)
        grain0.pixel_aspect_ratio = 1
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'video')
        self.assertEqual(segments[1][0].format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(segments[1][0].width, 1920)
        self.assertEqual(segments[1][0].height, 1080)
        self.assertEqual(segments[1][0].source_aspect_ratio, Fraction(16, 9))
        self.assertEqual(segments[1][0].pixel_aspect_ratio, Fraction(1, 1))

        self.assertEqual(segments[1][0].data, grain0.data)

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'video')
        self.assertEqual(segments[1][1].format, CogFrameFormat.S16_422_10BIT)
        self.assertEqual(segments[1][1].width, 1920)
        self.assertEqual(segments[1][1].height, 1080)
        self.assertEqual(segments[1][1].source_aspect_ratio, 0)
        self.assertEqual(segments[1][1].pixel_aspect_ratio, 0)

        self.assertEqual(segments[1][1].data, grain1.data)

    def test_dumps_audiograins(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = AudioGrain(src_id, flow_id, cog_audio_format=CogAudioFormat.S16_PLANES, samples=1920, sample_rate=48000)
        grain1 = AudioGrain(src_id, flow_id, cog_audio_format=CogAudioFormat.S16_PLANES, samples=1920, sample_rate=48000)
        for i in range(0,len(grain0.data)):
            grain0.data[i] = i & 0xFF
        for i in range(0,len(grain1.data)):
            grain1.data[i] = 0xFF - (i & 0xFF)
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'audio')
        self.assertEqual(segments[1][0].format, CogAudioFormat.S16_PLANES)
        self.assertEqual(segments[1][0].samples, 1920)
        self.assertEqual(segments[1][0].sample_rate, 48000)

        self.assertEqual(segments[1][0].data, grain0.data)

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'audio')
        self.assertEqual(segments[1][1].format, CogAudioFormat.S16_PLANES)
        self.assertEqual(segments[1][1].samples, 1920)
        self.assertEqual(segments[1][1].sample_rate, 48000)

        self.assertEqual(segments[1][1].data, grain1.data)

    def test_dumps_codedvideograins(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = CodedVideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.VC2, origin_width=1920, origin_height=1080, coded_width=1920,
                                 coded_height=1088, is_key_frame=True, temporal_offset=-23, length=1024, unit_offsets=[5, 15, 105])
        grain1 = CodedVideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.VC2, origin_width=1920, origin_height=1080, coded_width=1920,
                                 coded_height=1088, temporal_offset=17, length=256)
        for i in range(0,len(grain0.data)):
            grain0.data[i] = i & 0xFF
        for i in range(0,len(grain1.data)):
            grain1.data[i] = 0xFF - (i & 0xFF)
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'coded_video')
        self.assertEqual(segments[1][0].format, CogFrameFormat.VC2)
        self.assertEqual(segments[1][0].origin_width, 1920)
        self.assertEqual(segments[1][0].origin_height, 1080)
        self.assertEqual(segments[1][0].coded_width, 1920)
        self.assertEqual(segments[1][0].coded_height, 1088)
        self.assertEqual(segments[1][0].temporal_offset, -23)
        self.assertEqual(segments[1][0].unit_offsets, [5, 15, 105])
        self.assertTrue(segments[1][0].is_key_frame)

        self.assertEqual(segments[1][0].data, grain0.data)

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'coded_video')
        self.assertEqual(segments[1][1].format, CogFrameFormat.VC2)
        self.assertEqual(segments[1][1].origin_width, 1920)
        self.assertEqual(segments[1][1].origin_height, 1080)
        self.assertEqual(segments[1][1].coded_width, 1920)
        self.assertEqual(segments[1][1].coded_height, 1088)
        self.assertEqual(segments[1][1].temporal_offset, 17)
        self.assertEqual(segments[1][1].unit_offsets, [])
        self.assertFalse(segments[1][1].is_key_frame)

        self.assertEqual(segments[1][1].data, grain1.data)

    def test_dumps_codedaudiograins(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = CodedAudioGrain(src_id, flow_id, cog_audio_format=CogAudioFormat.AAC, samples=1920, sample_rate=48000, priming=23, remainder=17, length=1024)
        grain1 = CodedAudioGrain(src_id, flow_id, cog_audio_format=CogAudioFormat.AAC, samples=1920, sample_rate=48000, priming=5, remainder=104, length=1500)
        for i in range(0,len(grain0.data)):
            grain0.data[i] = i & 0xFF
        for i in range(0,len(grain1.data)):
            grain1.data[i] = 0xFF - (i & 0xFF)
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'coded_audio')
        self.assertEqual(segments[1][0].format, CogAudioFormat.AAC)
        self.assertEqual(segments[1][0].samples, 1920)
        self.assertEqual(segments[1][0].sample_rate, 48000)
        self.assertEqual(segments[1][0].priming, 23)
        self.assertEqual(segments[1][0].remainder, 17)

        self.assertEqual(segments[1][0].data, grain0.data)

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'coded_audio')
        self.assertEqual(segments[1][1].format, CogAudioFormat.AAC)
        self.assertEqual(segments[1][1].samples, 1920)
        self.assertEqual(segments[1][1].sample_rate, 48000)
        self.assertEqual(segments[1][1].priming, 5)
        self.assertEqual(segments[1][1].remainder, 104)

        self.assertEqual(segments[1][1].data, grain1.data)

    def test_dumps_eventgrains(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = EventGrain(src_id, flow_id)
        grain0.event_type = "urn:x-testing:stupid/type"
        grain0.topic = "/watashi"
        grain0.append("/inu", post="desu")
        grain1 = EventGrain(src_id, flow_id)
        grain1.event_type = "urn:x-testing:clever/type"
        grain1.topic = "/inu"
        grain1.append("/sukimono", pre="da")
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'event')
        self.assertEqual(segments[1][0].event_type, "urn:x-testing:stupid/type")
        self.assertEqual(segments[1][0].topic, "/watashi")
        self.assertEqual(len(segments[1][0].event_data), 1)
        self.assertEqual(segments[1][0].event_data[0].path, "/inu")
        self.assertIsNone(segments[1][0].event_data[0].pre)
        self.assertEqual(segments[1][0].event_data[0].post, "desu")

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'event')
        self.assertEqual(segments[1][1].event_type, "urn:x-testing:clever/type")
        self.assertEqual(segments[1][1].topic, "/inu")
        self.assertEqual(len(segments[1][1].event_data), 1)
        self.assertEqual(segments[1][1].event_data[0].path, "/sukimono")
        self.assertEqual(segments[1][1].event_data[0].pre, "da")
        self.assertIsNone(segments[1][1].event_data[0].post)

    def test_dumps_emptygrains(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = Grain(src_id, flow_id)
        grain0.timelabels = [{
            'tag': 'tiggle',
            'timelabel': {
                'frames_since_midnight': 7,
                'frame_rate_numerator': 300,
                'frame_rate_denominator': 1,
                'drop_frame': False
            }
        }]
        grain1 = Grain(src_id, flow_id)
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([grain0, grain1]))

        self.assertIn('id', head)
        self.assertIn(head['id'], uuids)
        self.assertIn('tags', head)
        self.assertEqual(len(head['tags']), 0)
        self.assertIn('created', head)
        self.assertEqual(head['created'], created)
        self.assertIn('segments', head)
        self.assertEqual(len(head['segments']), 1)
        self.assertIn('count', head['segments'][0])
        self.assertEqual(head['segments'][0]['count'], 2)
        self.assertIn('local_id', head['segments'][0])
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertIn('id', head['segments'][0])
        self.assertIn(head['segments'][0]['id'], uuids)
        self.assertIn('tags', head['segments'][0])
        self.assertEqual(len(head['segments'][0]['tags']), 0)

        self.assertEqual(len(segments), 1)
        self.assertIn(1, segments)
        self.assertEqual(len(segments[1]), head['segments'][0]['count'])

        self.assertEqual(segments[1][0].source_id, src_id)
        self.assertEqual(segments[1][0].flow_id, flow_id)
        self.assertEqual(segments[1][0].grain_type, 'empty')
        self.assertEqual(segments[1][0].timelabels,  [{
            'tag': 'tiggle',
            'timelabel': {
                'frames_since_midnight': 7,
                'frame_rate_numerator': 300,
                'frame_rate_denominator': 1,
                'drop_frame': False
            }
        }])
        self.assertIsNone(segments[1][0].data)

        self.assertEqual(segments[1][1].source_id, src_id)
        self.assertEqual(segments[1][1].flow_id, flow_id)
        self.assertEqual(segments[1][1].grain_type, 'empty')
        self.assertIsNone(segments[1][1].data)

    def test_dumps_invalidgrains(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain = Grain(src_id, flow_id)
        grain.grain_type = "invalid"
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with self.assertRaises(GSFEncodeError):
            with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
                with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                    (head, segments) = loads(dumps([grain]))

    def test_dump_progressively(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        grain1 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)

        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)

        file = BytesIO()
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                enc = GSFEncoder(file)
                enc.add_segment()
                self.assertEqual(len(file.getvalue()), 0)
                enc.start_dump()
                dump0 = file.getvalue()
                (head0, segments0) = loads(dump0)
                enc.add_grain(grain0)
                dump1 = file.getvalue()
                (head1, segments1) = loads(dump1)
                enc.add_grain(grain1, segment_local_id=1)
                dump2 = file.getvalue()
                (head2, segments2) = loads(dump2)
                enc.end_dump()
                dump3 = file.getvalue()
                (head3, segments3) = loads(dump3)

        self.assertEqual(head0['segments'][0]['count'], -1)
        self.assertEqual(head1['segments'][0]['count'], -1)
        self.assertEqual(head2['segments'][0]['count'], -1)
        self.assertEqual(head3['segments'][0]['count'], 2)

        if 1 in segments0:
            self.assertEqual(len(segments0[1]), 0)
        self.assertEqual(len(segments1[1]), 1)
        self.assertEqual(len(segments2[1]), 2)
        self.assertEqual(len(segments3[1]), 2)

    def test_end_dump_without_start_does_nothing(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        grain1 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)

        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)

        file = BytesIO()
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                enc = GSFEncoder(file)
                enc.add_segment()
                dump0 = file.getvalue()
                enc.end_dump()
                dump1 = file.getvalue()

        self.assertEqual(dump0, dump1)

    def test_dumps_fails_with_invalid_tags(self):
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with self.assertRaises(GSFEncodeError):
            with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
                with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                    (head, segments) = loads(dumps([], tags=[None, None]))

    def test_dumps_can_set_tags(self):
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                (head, segments) = loads(dumps([], tags=[('potato', 'harvest')], segment_tags=[('rainbow', 'dash')]))

        self.assertEqual(len(head['tags']), 1)
        self.assertIn(('potato', 'harvest'), head['tags'])

        self.assertEqual(len(head['segments'][0]['tags']), 1)
        self.assertIn(('rainbow', 'dash'), head['segments'][0]['tags'])

    def test_encoder_access_methods(self):
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                enc = GSFEncoder([], tags=[('potato', 'harvest')])
                enc.add_segment(tags=[('rainbow', 'dash')])

        self.assertEqual(enc.tags, (('potato', 'harvest'),))
        self.assertIsInstance(enc.segments, frozendict)
        self.assertEqual(enc.segments[1].tags, (('rainbow', 'dash'),))

    def test_encoder_raises_when_adding_to_active_encode(self):
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        file = BytesIO()
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                enc = GSFEncoder(file, tags=[('potato', 'harvest')])
                seg = enc.add_segment(tags=[('rainbow', 'dash')])

        with self.assertRaises(GSFEncodeError):
            enc.add_segment(local_id=1)

        with self.assertRaises(GSFEncodeError):
            enc.add_segment(tags=[None])

        enc.start_dump()

        with self.assertRaises(GSFEncodeAddToActiveDump):
            enc.add_tag('upside', 'down')
        with self.assertRaises(GSFEncodeAddToActiveDump):
            enc.add_segment()
        with self.assertRaises(GSFEncodeAddToActiveDump):
            seg.add_tag('upside', 'down')

    def test_encoder_can_add_grains_to_nonexistent_segment(self):
        src_id = UUID('e14e9d58-1567-11e8-8dd3-831a068eb034')
        flow_id = UUID('ee1eed58-1567-11e8-a971-3b901a2dd8ab')
        grain0 = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
        uuids = [UUID('7920b394-1565-11e8-86e0-8b42d4647ba8'),
                 UUID('80af875c-1565-11e8-8f44-87ef081b48cd')]
        created = datetime(1983, 3, 29, 15, 15)
        file = BytesIO()
        with mock.patch('mediagrains.gsf.datetime', side_effect=datetime, now=mock.MagicMock(return_value=created)):
            with mock.patch('mediagrains.gsf.uuid1', side_effect=uuids):
                enc = GSFEncoder(file, tags=[('potato', 'harvest')])

        enc.add_grain(grain0, segment_local_id=2)

        self.assertEqual(enc.segments[2].grains[0], grain0)


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

    def test_load_video(self):
        file = BytesIO(VIDEO_DATA)
        (head, segments) = load(file)

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
        unit_offsets = [
            ([0, 6, 34, 42, 711, 719], 36114),
            ([0, 6, 14], 380),
            ([0, 6, 14], 8277),
            ([0, 6, 14], 4914),
            ([0, 6, 14], 4961),
            ([0, 6, 14], 3777),
            ([0, 6, 14], 1950),
            ([0, 6, 14], 31),
            ([0, 6, 14], 25),
            ([0, 6, 14], 6241)]
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
            self.assertEqual(grain.length, unit_offsets[0][1])
            self.assertEqual(grain.temporal_offset, 0)
            self.assertEqual(grain.unit_offsets, unit_offsets[0][0])
            unit_offsets.pop(0)

    def test_loads_rejects_incorrect_type_file(self):
        with self.assertRaises(GSFDecodeBadFileTypeError) as cm:
            loads(b"POTATO23\x07\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.filetype, "POTATO23")

    def test_loads_rejects_incorrect_version_file(self):
        with self.assertRaises(GSFDecodeBadVersionError) as cm:
            loads(b"SSBBgrsg\x08\x00\x03\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.major, 8)
        self.assertEqual(cm.exception.minor, 3)

    def test_loads_rejects_bad_head_tag(self):
        with self.assertRaises(GSFDecodeError) as cm:
            loads(b"SSBBgrsg\x07\x00\x00\x00" +
                  b"\xff\xff\xff\xff\x00\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 12)

    def test_loads_raises_exception_without_head(self):
        with self.assertRaises(GSFDecodeError) as cm:
            loads(b"SSBBgrsg\x07\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 12)

    def test_loads_skips_unknown_block_before_head(self):
        (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                 b"dumy\x08\x00\x00\x00" +
                                 b"head\x1f\x00\x00\x00" +
                                 b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                 b"\xbf\x07\x03\x1d\x0f\x0f\x0f")

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(head['segments'], [])
        self.assertEqual(head['tags'], [])

    def test_loads_skips_unknown_block_instead_of_segm(self):
        (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                 b"head\x27\x00\x00\x00" +
                                 b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                 b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                 b"dumy\x08\x00\x00\x00")

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(head['segments'], [])
        self.assertEqual(head['tags'], [])

    def test_loads_skips_unknown_block_before_segm(self):
        (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                   (b"head\x49\x00\x00\x00" +
                                    b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                    b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                      (b"dumy\x08\x00\x00\x00") +
                                      (b"segm\x22\x00\x00\x00" +
                                       b"\x01\x00" +
                                       b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00")))

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertEqual(head['segments'][0]['id'], UUID('d3e191f0-1594-11e8-91ac-dca904824eec'))
        self.assertEqual(head['segments'][0]['tags'], [])
        self.assertEqual(head['segments'][0]['count'], 0)
        self.assertEqual(head['tags'], [])

    def test_loads_raises_when_head_too_small(self):
        with self.assertRaises(GSFDecodeError) as cm:
            (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                    (b"head\x27\x00\x00\x00" +
                                     b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                     b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                       (b"dumy\x08\x00\x00\x00") +
                                       (b"segm\x22\x00\x00\x00" +
                                        b"\x01\x00" +
                                        b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                        b"\x00\x00\x00\x00\x00\x00\x00\x00")))

        self.assertEqual(cm.exception.offset, 12)

    def test_loads_raises_when_segm_too_small(self):
        with self.assertRaises(GSFDecodeError) as cm:
            (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                    (b"head\x41\x00\x00\x00" +
                                     b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                     b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                       (b"segm\x21\x00\x00\x00" +
                                        b"\x01\x00" +
                                        b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                        b"\x00\x00\x00\x00\x00\x00\x00\x00")))

        self.assertEqual(cm.exception.offset, 43)

    def test_loads_decodes_tils(self):
        src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
        flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
        (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                   (b"head\x41\x00\x00\x00" +
                                    b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                    b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                      (b"segm\x22\x00\x00\x00" +
                                       b"\x01\x00" +
                                       b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                       b"\x01\x00\x00\x00\x00\x00\x00\x00")) +
                                   (b"grai\x8d\x00\x00\x00" +
                                    b"\x01\x00" +
                                      (b"gbhd\x83\x00\x00\x00" +
                                       src_id.bytes +
                                       flow_id.bytes +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                         (b"tils\x27\x00\x00\x00" +
                                          b"\x01\x00" +
                                          b"dummy timecode\x00\x00" +
                                          b"\x07\x00\x00\x00" +
                                          b"\x19\x00\x00\x00\x01\x00\x00\x00" +
                                          b"\x00"))) +
                                   (b"grai\x08\x00\x00\x00"))

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['local_id'], 1)
        self.assertEqual(head['segments'][0]['id'], UUID('d3e191f0-1594-11e8-91ac-dca904824eec'))
        self.assertEqual(head['segments'][0]['tags'], [])
        self.assertEqual(head['segments'][0]['count'], 1)
        self.assertEqual(head['tags'], [])
        self.assertEqual(segments[1][0].timelabels, [{'tag': 'dummy timecode', 'timelabel': {'frames_since_midnight': 7,
                                                                                             'frame_rate_numerator': 25,
                                                                                             'frame_rate_denominator': 1,
                                                                                             'drop_frame': False}}])

    def test_loads_raises_when_grain_type_unknown(self):
        with self.assertRaises(GSFDecodeError) as cm:
            src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
            flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
            (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                       (b"head\x41\x00\x00\x00" +
                                        b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                        b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                          (b"segm\x22\x00\x00\x00" +
                                           b"\x01\x00" +
                                           b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                           b"\x01\x00\x00\x00\x00\x00\x00\x00")) +
                                       (b"grai\x8d\x00\x00\x00" +
                                        b"\x01\x00" +
                                          (b"gbhd\x83\x00\x00\x00" +
                                           src_id.bytes +
                                           flow_id.bytes +
                                           b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                           b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                           b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                           b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                           b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                             (b"dumy\x08\x00\x00\x00"))))

        self.assertEqual(cm.exception.offset, 87)

    def test_loads_decodes_empty_grains(self):
        src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
        flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
        (head, segments) = loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                   (b"head\x41\x00\x00\x00" +
                                    b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                    b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                      (b"segm\x22\x00\x00\x00" +
                                       b"\x01\x00" +
                                       b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                       b"\x02\x00\x00\x00\x00\x00\x00\x00")) +
                                   (b"grai\x66\x00\x00\x00" +
                                    b"\x01\x00" +
                                      (b"gbhd\x5c\x00\x00\x00" +
                                       src_id.bytes +
                                       flow_id.bytes +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00")) +
                                   (b"dumy\x08\x00\x00\x00") +
                                   (b"grai\x6E\x00\x00\x00" +
                                    b"\x01\x00" +
                                      (b"gbhd\x5c\x00\x00\x00" +
                                       src_id.bytes +
                                       flow_id.bytes +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00" +
                                       b"\x00\x00\x00\x00\x00\x00\x00\x00") +
                                      (b"grdt\x08\x00\x00\x00")) +
                                   (b"dumy\x08\x00\x00\x00"))

        self.assertEqual(len(segments[1]), 2)
        self.assertEqual(segments[1][0].grain_type, "empty")
        self.assertIsNone(segments[1][0].data)
        self.assertEqual(segments[1][1].grain_type, "empty")
        self.assertIsNone(segments[1][1].data)

    def test_loads_coded_audio(self):
        (head, segments) = loads(CODED_AUDIO_DATA)

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 38, 5))
        self.assertEqual(head['id'], UUID('2dbc5889-15f1-427c-b727-5201dd3b053c'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('6ca3a217-f2c2-4344-832b-6ea87bc5ddb8'))
        self.assertIn(head['segments'][0]['local_id'], segments)
        self.assertEqual(len(segments[head['segments'][0]['local_id']]), head['segments'][0]['count'])

        start_ots = Timestamp(1420102800, 0)
        ots = start_ots
        total_samples = 0
        lengths = [603,
                   690,
                   690,
                   689,
                   690,
                   690,
                   689,
                   690,
                   690,
                   689]
        for grain in segments[head['segments'][0]['local_id']]:
            self.assertIsInstance(grain, CODEDAUDIOGRAIN)
            self.assertEqual(grain.grain_type, "coded_audio")
            self.assertEqual(grain.source_id, UUID('38bfd902-b35f-40d6-9ecf-dc95869130cf'))
            self.assertEqual(grain.flow_id, UUID('e615296b-ff40-4d95-8398-6a4082305f3a'))
            self.assertEqual(grain.origin_timestamp, ots)

            self.assertEqual(grain.format, CogAudioFormat.AAC)
            self.assertEqual(grain.channels, 2)
            self.assertEqual(grain.samples, 1024)
            self.assertEqual(grain.priming, 0)
            self.assertEqual(grain.remainder, 0)
            self.assertEqual(grain.sample_rate, 48000)

            self.assertEqual(len(grain.data), lengths[0])
            lengths.pop(0)
            total_samples += grain.samples
            ots = start_ots + TimeOffset.from_count(total_samples, grain.sample_rate)

    def test_loads_event(self):
        self.maxDiff = None
        (head, segments) = loads(EVENT_DATA)

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 37, 35))
        self.assertEqual(head['id'], UUID('3c45f8b5-1853-4723-808a-ab5cbf598ccc'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('db095cb5-050b-4b8c-92e8-31351422e93a'))
        self.assertIn(head['segments'][0]['local_id'], segments)
        self.assertEqual(len(segments[head['segments'][0]['local_id']]), head['segments'][0]['count'])

        start_ots = Timestamp(1447176512, 400000000)
        ots = start_ots
        line = ''
        seqnum = 3107787894242499264
        for grain in segments[head['segments'][0]['local_id']]:
            self.assertIsInstance(grain, EVENTGRAIN)
            self.assertEqual(grain.grain_type, "event")
            self.assertEqual(grain.source_id, UUID('2db4268e-82ef-49f9-bc0f-1726e8352d76'))
            self.assertEqual(grain.flow_id, UUID('5333bae9-0768-4e31-be1c-fbd5dc2e34ac'))
            self.assertEqual(grain.origin_timestamp, ots)

            self.assertEqual(grain.event_type, 'urn:x-ipstudio:format:event.ttext.ebuttlive')
            self.assertEqual(grain.topic, '')
            self.assertEqual(len(grain.event_data), 1)
            self.assertEqual(grain.event_data[0].path, 'Subs')
            self.assertEqual(grain.event_data[0].pre, line)
            line = '<?xml version="1.0" encoding="UTF-8"?>\n<tt:tt ttp:timeBase="clock" ttp:clockMode="utc" xml:lang="en" xmlns:tt="http://www.w3.org/ns/ttml"  xmlns:ebuttExt="urn:ebu:tt:extension"  xmlns:ttp="http://www.w3.org/ns/ttml#parameter" xmlns:tts="http://www.w3.org/ns/ttml#styling" ttp:cellResolution="50 30" xmlns:ebuttm="urn:ebu:tt:metadata" tts:extent="1920px 1080px" ttp:dropMode="nonDrop" ttp:markerMode="discontinuous" ebuttm:sequenceIdentifier="5333bae9-0768-4e31-be1c-fbd5dc2e34ac" ebuttm:sequenceNumber="' + str(seqnum) + '"><tt:head><tt:metadata><ebuttm:documentMetadata><ebuttm:documentEbuttVersion>v1.0</ebuttm:documentEbuttVersion><ebuttm:documentTotalNumberOfSubtitles>1</ebuttm:documentTotalNumberOfSubtitles><ebuttm:documentMaximumNumberOfDisplayableCharacterInAnyRow>40</ebuttm:documentMaximumNumberOfDisplayableCharacterInAnyRow><ebuttm:documentCountryOfOrigin>gb</ebuttm:documentCountryOfOrigin></ebuttm:documentMetadata></tt:metadata><tt:styling><tt:style xml:id="defaultStyle" tts:fontFamily="monospaceSansSerif" tts:fontSize="1c 1c" tts:lineHeight="normal" tts:textAlign="center" tts:color="white" tts:backgroundColor="transparent" tts:fontStyle="normal" tts:fontWeight="normal" tts:textDecoration="none" /><tt:style xml:id="WhiteOnBlack" tts:color="white" tts:backgroundColor="black" tts:fontSize="1c 2c"/><tt:style xml:id="textCenter" tts:textAlign="center"/></tt:styling><tt:layout><tt:region xml:id="bottom" tts:origin="10% 10%" tts:extent="80% 80%" tts:padding="0c" tts:displayAlign="after" tts:writingMode="lrtb"/></tt:layout></tt:head><tt:body dur="00:00:10"><tt:div style="defaultStyle"><tt:p xml:id="sub2" style="textCenter" region="bottom"><tt:span style="WhiteOnBlack">' + ots.to_iso8601_utc() + '</tt:span></tt:p></tt:div></tt:body></tt:tt>' # NOQA
            self.assertEqual(grain.event_data[0].post, line, msg="\n\nExpected:\n\n{!r}\n\nGot:\n\n{!r}\n\n".format(line, grain.event_data[0].post))

            ots = ots + TimeOffset.from_nanosec(20000000)
            seqnum += 20000000