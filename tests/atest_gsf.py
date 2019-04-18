#!/usr/bin/python
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

from unittest import TestCase
import mock
import asyncio
import warnings
import aiofiles
from datetime import datetime
from uuid import UUID

from mediagrains.async import AsyncGSFDecoder, AsyncLazyLoaderUnloadedError
from mediagrains.grain import VIDEOGRAIN, AUDIOGRAIN, CODEDVIDEOGRAIN, CODEDAUDIOGRAIN, EVENTGRAIN


def async_test(f):
    def __inner(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)
        E = None
        warns = []

        try:
            with warnings.catch_warnings(record=True) as warns:
                loop.run_until_complete(f(*args, **kwargs))

        except AssertionError as e:
            E = e
        except Exception as e:
            E = e

        for w in warns:
            warnings.showwarning(w.message,
                                 w.category,
                                 w.filename,
                                 w.lineno)
        if E is None:
            args[0].assertEqual(len(warns), 0,
                                msg="asyncio subsystem generated warnings due to unawaited coroutines")
        else:
            raise E

    return __inner


class TestAsyncGSFBlock (TestCase):
    @async_test
    async def test_decode_headers(self):
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            UUT = AsyncGSFDecoder(file_data=video_data_stream)
            head = await UUT.decode_file_headers()

        self.assertEqual(head['created'], datetime(2018, 2, 7, 10, 38, 22))
        self.assertEqual(head['id'], UUID('163fd9b7-bef4-4d92-8488-31f3819be008'))
        self.assertEqual(len(head['segments']), 1)
        self.assertEqual(head['segments'][0]['id'], UUID('c6a3d3ff-74c0-446d-b59e-de1041f27e8a'))

    @async_test
    async def test_generate_grains(self):
        """Test that the generator yields each grain"""
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            UUT = AsyncGSFDecoder(file_data=video_data_stream)
            await UUT.decode_file_headers()

            grain_count = 0
            async for (grain, local_id) in UUT.grains():
                self.assertIsInstance(grain, VIDEOGRAIN)
                self.assertEqual(grain.source_id, UUID('49578552-fb9e-4d3e-a197-3e3c437a895d'))
                self.assertEqual(grain.flow_id, UUID('6e55f251-f75a-4d56-b3af-edb8b7993c3c'))

                grain_count += 1

        self.assertEqual(10, grain_count)  # There are 10 grains in the file

    @async_test
    async def test_local_id_filtering(self):
        async with aiofiles.open('examples/interleaved.gsf', 'rb') as interleaved_data_stream:
            UUT = AsyncGSFDecoder(file_data=interleaved_data_stream)
            await UUT.decode_file_headers()

            local_ids = set()
            flow_ids = set()
            async for (grain, local_id) in UUT.grains():
                local_ids.add(local_id)
                flow_ids.add(grain.flow_id)

            self.assertEqual(local_ids, set([1, 2]))
            self.assertEqual(flow_ids, set([UUID('28e4e09e-3517-11e9-8da2-5065f34ed007'),
                                            UUID('2472f38e-3517-11e9-8da2-5065f34ed007')]))

            await interleaved_data_stream.seek(0)
            await UUT.decode_file_headers()

            async for (grain, local_id) in UUT.grains(local_ids=[1]):
                self.assertIsInstance(grain, AUDIOGRAIN)
                self.assertEqual(grain.source_id, UUID('1f8fd27e-3517-11e9-8da2-5065f34ed007'))
                self.assertEqual(grain.flow_id, UUID('28e4e09e-3517-11e9-8da2-5065f34ed007'))
                self.assertEqual(local_id, 1)

            await interleaved_data_stream.seek(0)
            await UUT.decode_file_headers()

            async for (grain, local_id) in UUT.grains(local_ids=[2]):
                self.assertIsInstance(grain, VIDEOGRAIN)
                self.assertEqual(grain.source_id, UUID('1f8fd27e-3517-11e9-8da2-5065f34ed007'))
                self.assertEqual(grain.flow_id, UUID('2472f38e-3517-11e9-8da2-5065f34ed007'))
                self.assertEqual(local_id, 2)

    @async_test
    async def test_lazy_loading(self):
        async with aiofiles.open('examples/video.gsf', 'rb') as video_data_stream:
            UUT = AsyncGSFDecoder(file_data=video_data_stream)
            await UUT.decode_file_headers()

            grains = [grain async for (grain, local_id) in UUT.grains()]

            with self.assertRaises(AsyncLazyLoaderUnloadedError):
                grains[0].data[0]

            await grains[0].data.load()

            self.assertEqual(grains[0].data[0:1024], b"\x10" * 1024)
