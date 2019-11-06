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

"""\
A simple wrapper class BytesAIO which is an asynchronous version of BytesIO
"""

from io import BytesIO


def asynchronise(f):
    async def __inner(*args, **kwargs):
        return f(*args, **kwargs)
    return __inner


class BytesAIO(object):
    def __init__(self, b):
        """Constructor

        :param s: A bytes object"""
        self._bytesio = BytesIO(b)

    def __getattr__(self, attr):
        if attr in ['getbuffer',
                    'getvalue',
                    'closed']:
            return getattr(self._bytesio, attr)
        elif attr in ['read1',
                      'readinto1',
                      'detach',
                      'read',
                      'readinto',
                      'write',
                      'close',
                      'fileno',
                      'flush',
                      'isatty',
                      'readable',
                      'readline',
                      'readlines',
                      'seek',
                      'seekable',
                      'tell',
                      'truncate',
                      'writeable',
                      'writelines']:
            return asynchronise(getattr(self._bytesio, attr))
        else:
            raise AttributeError

    async def __aenter__(self):
        return self._bytesio.__enter__()

    async def __aexit__(self, *args, **kwargs):
        return self._bytesio.__exit__(*args, **kwargs)

    def __aiter__(self):
        return self

    def __anext__(self):
        return next(self._bytesio)
