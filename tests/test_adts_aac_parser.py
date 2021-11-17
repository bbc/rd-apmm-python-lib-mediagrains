# Copyright 2021 British Broadcasting Corporation
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

from unittest import IsolatedAsyncioTestCase
import os

from mediagrains.utils.adts_aac_parser import ADTSAACParser, MIN_ADTS_HEADER_SIZE

TEST_FILE = os.path.dirname(__file__) + "/audio.aac"


class TestADTSAACParser(IsolatedAsyncioTestCase):
    def setUp(self):
        self.uut = ADTSAACParser()

    def test_parse(self):
        """Check the ADTS AAC frame can be parsed correctly"""
        with open(TEST_FILE, "rb") as f:
            data = f.read(MIN_ADTS_HEADER_SIZE)
            frame_info = self.uut.parse_header(data)

            self.assertEqual(frame_info.frame_size, 603)
            self.assertEqual(frame_info.object_type, 1)
            self.assertEqual(frame_info.sample_rate, 48000)
            self.assertEqual(frame_info.channels, 2)

    def test_parse__invalid(self):
        """Check invalid data raises a ValueError"""
        data = bytearray(MIN_ADTS_HEADER_SIZE)
        with self.assertRaises(ValueError):
            self.uut.parse_header(data)

    def test_parse__insufficient(self):
        """Check insufficient data raises a ValueError"""
        data = bytearray(MIN_ADTS_HEADER_SIZE - 1)
        with self.assertRaises(ValueError):
            self.uut.parse_header(data)
