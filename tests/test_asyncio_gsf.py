# -*- coding: utf-8 -*-
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


#
# The code these tests test is deprecated
#
# The tests remain until the code is removed
#


from unittest import TestCase
import aiofiles
from datetime import datetime
from uuid import UUID

from fixtures import async_test

from mediagrains.asyncio import AsyncGSFDecoder, AsyncLazyLoaderUnloadedError, loads
from mediagrains.grain import VIDEOGRAIN, AUDIOGRAIN, EVENTGRAIN, CODEDVIDEOGRAIN, CODEDAUDIOGRAIN
from mediagrains.gsf import GSFDecodeError
from mediagrains.gsf import GSFDecodeBadVersionError
from mediagrains.gsf import GSFDecodeBadFileTypeError
from mediagrains.cogenums import CogFrameFormat, CogFrameLayout, CogAudioFormat

from mediatimestamp.immutable import Timestamp, TimeOffset


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

with open('examples/interleaved.gsf', 'rb') as f:
    INTERLEAVED_DATA = f.read()


class TestAsyncGSFBlock (TestCase):
    @async_test(suppress_warnings=True)
    async def test_decode_headers(self):
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            UUT = AsyncGSFDecoder(file_data=video_data_stream)
            head = await UUT.decode_file_headers()

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 38, 22))
        self.assertEqual(head['id'], UUID('163fd9b7-bef4-4d92-8488-31f3819be008'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('c6a3d3ff-74c0-446d-b59e-de1041f27e8a'))

    @async_test(suppress_warnings=True)
    async def test_generate_grains(self):
        """Test that the generator yields each grain"""
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            grain_count = 0
            async for (grain, local_id) in AsyncGSFDecoder(file_data=video_data_stream).grains():
                self.assertIsInstance(grain, VIDEOGRAIN)
                self.assertEqual(grain.source_id, UUID('49578552-fb9e-4d3e-a197-3e3c437a895d'))
                self.assertEqual(grain.flow_id, UUID('6e55f251-f75a-4d56-b3af-edb8b7993c3c'))

                grain_count += 1

        self.assertEqual(10, grain_count)  # There are 10 grains in the file

    @async_test(suppress_warnings=True)
    async def test_local_id_filtering(self):
        async with aiofiles.open('examples/interleaved.gsf', 'rb') as interleaved_data_stream:
            async with AsyncGSFDecoder(file_data=interleaved_data_stream) as UUT:
                local_ids = set()
                flow_ids = set()
                async for (grain, local_id) in UUT.grains():
                    local_ids.add(local_id)
                    flow_ids.add(grain.flow_id)

                self.assertEqual(local_ids, set([1, 2]))
                self.assertEqual(flow_ids, set([UUID('28e4e09e-3517-11e9-8da2-5065f34ed007'),
                                                UUID('2472f38e-3517-11e9-8da2-5065f34ed007')]))

            async with AsyncGSFDecoder(file_data=interleaved_data_stream) as UUT:
                async for (grain, local_id) in UUT.grains(local_ids=[1]):
                    self.assertIsInstance(grain, AUDIOGRAIN)
                    self.assertEqual(grain.source_id, UUID('1f8fd27e-3517-11e9-8da2-5065f34ed007'))
                    self.assertEqual(grain.flow_id, UUID('28e4e09e-3517-11e9-8da2-5065f34ed007'))
                    self.assertEqual(local_id, 1)

            async with AsyncGSFDecoder(file_data=interleaved_data_stream) as UUT:
                async for (grain, local_id) in UUT.grains(local_ids=[2]):
                    self.assertIsInstance(grain, VIDEOGRAIN)
                    self.assertEqual(grain.source_id, UUID('1f8fd27e-3517-11e9-8da2-5065f34ed007'))
                    self.assertEqual(grain.flow_id, UUID('2472f38e-3517-11e9-8da2-5065f34ed007'))
                    self.assertEqual(local_id, 2)

    @async_test(suppress_warnings=True)
    async def test_lazy_loading(self):
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            grains = [grain async for (grain, local_id) in AsyncGSFDecoder(file_data=video_data_stream).grains()]

            with self.assertRaises(AsyncLazyLoaderUnloadedError):
                grains[0].data[0]

            await grains[0].data.load()

            self.assertEqual(grains[0].data[0:1024], b"\x10" * 1024)


class TestAsyncGSFLoads(TestCase):
    @async_test(suppress_warnings=True)
    async def test_loads_video(self):
        (head, segments) = await loads(VIDEO_DATA)

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
            self.assertEqual(grain.components[0].offset, 0)

            self.assertEqual(grain.components[1].width, 240)
            self.assertEqual(grain.components[1].height, 135)
            self.assertEqual(grain.components[1].stride, 240)
            self.assertEqual(grain.components[1].length, 240*135)
            self.assertEqual(grain.components[1].offset, 480*270)

            self.assertEqual(grain.components[2].width, 240)
            self.assertEqual(grain.components[2].height, 135)
            self.assertEqual(grain.components[2].stride, 240)
            self.assertEqual(grain.components[2].length, 240*135)
            self.assertEqual(grain.components[2].offset, 480*270 + 240*135)

            self.assertEqual(len(grain.data), grain.components[0].length + grain.components[1].length + grain.components[2].length)

    @async_test(suppress_warnings=True)
    async def test_loads_audio(self):
        (head, segments) = await loads(AUDIO_DATA)

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

    @async_test(suppress_warnings=True)
    async def test_loads_coded_video(self):
        (head, segments) = await loads(CODED_VIDEO_DATA)

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

    @async_test(suppress_warnings=True)
    async def test_loads_rejects_incorrect_type_file(self):
        with self.assertRaises(GSFDecodeBadFileTypeError) as cm:
            await loads(b"POTATO23\x07\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.filetype, "POTATO23")

    @async_test(suppress_warnings=True)
    async def test_loads_rejects_incorrect_version_file(self):
        with self.assertRaises(GSFDecodeBadVersionError) as cm:
            await loads(b"SSBBgrsg\x08\x00\x03\x00")
        self.assertEqual(cm.exception.offset, 0)
        self.assertEqual(cm.exception.major, 8)
        self.assertEqual(cm.exception.minor, 3)

    @async_test(suppress_warnings=True)
    async def test_loads_rejects_bad_head_tag(self):
        with self.assertRaises(GSFDecodeError) as cm:
            await loads(b"SSBBgrsg\x07\x00\x00\x00" +
                        b"\xff\xff\xff\xff\x00\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 12)

    @async_test(suppress_warnings=True)
    async def test_loads_raises_exception_without_head(self):
        with self.assertRaises(GSFDecodeError) as cm:
            await loads(b"SSBBgrsg\x07\x00\x00\x00")
        self.assertEqual(cm.exception.offset, 12)

    @async_test(suppress_warnings=True)
    async def test_loads_skips_unknown_block_before_head(self):
        (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                       b"dumy\x08\x00\x00\x00" +
                                       b"head\x1f\x00\x00\x00" +
                                       b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                       b"\xbf\x07\x03\x1d\x0f\x0f\x0f")

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(head['segments'], [])
        self.assertEqual(head['tags'], [])

    @async_test(suppress_warnings=True)
    async def test_loads_skips_unknown_block_instead_of_segm(self):
        (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                       b"head\x27\x00\x00\x00" +
                                       b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                       b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                       b"dumy\x08\x00\x00\x00")

        self.assertEqual(head['id'], UUID('d19c0b91-1590-11e8-8580-dca904824eec'))
        self.assertEqual(head['created'], datetime(1983, 3, 29, 15, 15, 15))
        self.assertEqual(head['segments'], [])
        self.assertEqual(head['tags'], [])

    @async_test(suppress_warnings=True)
    async def test_loads_skips_unknown_block_before_segm(self):
        (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
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

    @async_test(suppress_warnings=True)
    async def test_loads_raises_when_head_too_small(self):
        with self.assertRaises(GSFDecodeError) as cm:
            (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                           (b"head\x29\x00\x00\x00" +
                                            b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                            b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                            (b"dumy\x08\x00\x00\x00") +
                                            (b"segm\x22\x00\x00\x00" +
                                             b"\x01\x00" +
                                             b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                             b"\x00\x00\x00\x00\x00\x00\x00\x00")))

        self.assertEqual(cm.exception.offset, 51)

    @async_test(suppress_warnings=True)
    async def test_loads_raises_when_segm_too_small(self):
        with self.assertRaises(GSFDecodeError) as cm:
            (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
                                           (b"head\x41\x00\x00\x00" +
                                            b"\xd1\x9c\x0b\x91\x15\x90\x11\xe8\x85\x80\xdc\xa9\x04\x82N\xec" +
                                            b"\xbf\x07\x03\x1d\x0f\x0f\x0f" +
                                            (b"segm\x21\x00\x00\x00" +
                                             b"\x01\x00" +
                                             b"\xd3\xe1\x91\xf0\x15\x94\x11\xe8\x91\xac\xdc\xa9\x04\x82N\xec" +
                                             b"\x00\x00\x00\x00\x00\x00\x00\x00")))

        self.assertEqual(cm.exception.offset, 77)

    @async_test(suppress_warnings=True)
    async def test_loads_decodes_tils(self):
        src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
        flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
        (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
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

    @async_test(suppress_warnings=True)
    async def test_loads_raises_when_grain_type_unknown(self):
        with self.assertRaises(GSFDecodeError) as cm:
            src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
            flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
            (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
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

        self.assertEqual(cm.exception.offset, 179)

    @async_test(suppress_warnings=True)
    async def test_loads_decodes_empty_grains(self):
        src_id = UUID('c707d64c-1596-11e8-a3fb-dca904824eec')
        flow_id = UUID('da78668a-1596-11e8-a577-dca904824eec')
        (head, segments) = await loads(b"SSBBgrsg\x07\x00\x00\x00" +
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

    @async_test(suppress_warnings=True)
    async def test_loads_coded_audio(self):
        (head, segments) = await loads(CODED_AUDIO_DATA)

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

    @async_test(suppress_warnings=True)
    async def test_loads_event(self):
        self.maxDiff = None
        (head, segments) = await loads(EVENT_DATA)

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
            line = '<?xml version="1.0" encoding="UTF-8"?>\n<tt:tt ttp:timeBase="clock" ttp:clockMode="utc" xml:lang="en" xmlns:tt="http://www.w3.org/ns/ttml"  xmlns:ebuttExt="urn:ebu:tt:extension"  xmlns:ttp="http://www.w3.org/ns/ttml#parameter" xmlns:tts="http://www.w3.org/ns/ttml#styling" ttp:cellResolution="50 30" xmlns:ebuttm="urn:ebu:tt:metadata" tts:extent="1920px 1080px" ttp:dropMode="nonDrop" ttp:markerMode="discontinuous" ebuttm:sequenceIdentifier="5333bae9-0768-4e31-be1c-fbd5dc2e34ac" ebuttm:sequenceNumber="' + str(seqnum) + '"><tt:head><tt:metadata><ebuttm:documentMetadata><ebuttm:documentEbuttVersion>v1.0</ebuttm:documentEbuttVersion><ebuttm:documentTotalNumberOfSubtitles>1</ebuttm:documentTotalNumberOfSubtitles><ebuttm:documentMaximumNumberOfDisplayableCharacterInAnyRow>40</ebuttm:documentMaximumNumberOfDisplayableCharacterInAnyRow><ebuttm:documentCountryOfOrigin>gb</ebuttm:documentCountryOfOrigin></ebuttm:documentMetadata></tt:metadata><tt:styling><tt:style xml:id="defaultStyle" tts:fontFamily="monospaceSansSerif" tts:fontSize="1c 1c" tts:lineHeight="normal" tts:textAlign="center" tts:color="white" tts:backgroundColor="transparent" tts:fontStyle="normal" tts:fontWeight="normal" tts:textDecoration="none" /><tt:style xml:id="WhiteOnBlack" tts:color="white" tts:backgroundColor="black" tts:fontSize="1c 2c"/><tt:style xml:id="textCenter" tts:textAlign="center"/></tt:styling><tt:layout><tt:region xml:id="bottom" tts:origin="10% 10%" tts:extent="80% 80%" tts:padding="0c" tts:displayAlign="after" tts:writingMode="lrtb"/></tt:layout></tt:head><tt:body dur="00:00:10"><tt:div style="defaultStyle"><tt:p xml:id="sub2" style="textCenter" region="bottom"><tt:span style="WhiteOnBlack">' + ots.to_iso8601_utc() + '</tt:span></tt:p></tt:div></tt:body></tt:tt>'  # NOQA
            self.assertEqual(grain.event_data[0].post, line, msg="\n\nExpected:\n\n{!r}\n\nGot:\n\n{!r}\n\n".format(line, grain.event_data[0].post))

            ots = ots + TimeOffset.from_nanosec(20000000)
            seqnum += 20000000
