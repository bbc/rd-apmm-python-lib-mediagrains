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

from asynctest import TestCase, mock

from mediagrains.utils import IOBytes

from hypothesis import given
from hypothesis.strategies import integers

from io import BytesIO


TEST_DATA = b''.join(bytes(((x//256) % 256, (x % 256))) for x in range(0, 65536))


class IncorrectAccess (Exception):
    pass


class TestIOBytes (TestCase):

    @given(integers(min_value=0, max_value=65535), integers(min_value=0, max_value=65535))
    def test_read(self, start, length):
        iostream = BytesIO(TEST_DATA)
        orig_loc = iostream.tell()
        iobytes = IOBytes(iostream, start, length)
        data = bytes(iobytes)
        self.assertEqual(len(data), length)
        self.assertEqual(data, TEST_DATA[start:start + length])
        self.assertEqual(orig_loc, iostream.tell())

    def test_noread(self):
        iostream = mock.MagicMock()

        iobytes = IOBytes(iostream, 0, 60)
        iostream.assert_not_called()

        self.assertEqual(len(iobytes), 60)
        iostream.assert_not_called()

        repr(iobytes)
        iostream.assert_not_called()

        iostream.read.return_value.__getitem__.side_effect = lambda n: n

        self.assertEqual(iobytes[12], 12)
        self.assertEqual(len(iobytes), iostream.read.return_value.__len__.return_value)
