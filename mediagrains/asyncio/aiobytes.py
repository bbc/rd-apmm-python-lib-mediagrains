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
A simple wrapper class AsyncIOBytes which is an asynchronous version of IOBytes
"""

from collections.abc import Sequence
from typing import List


__all__ = ["AsyncIOBytes"]


class AsyncLazyLoaderUnloadedError (Exception):
    pass


class AsyncLazyLoader (object):
    """An object that can be loaded asynchronously as needed.

    In most cases this class should be subclassed to make actually useful classes, but technically it's not
    an abstract base class because it *can* be used directly if needed.

    The constructor takes a coroutine taking no parameters which returns an object as its only parameter.

    Unlike the synchronous version loading is not automatic, but can be triggered by awaiting the load coroutine.
    """

    _attributes: List[str] = []

    def __init__(self, loader):
        """
        :param loader: a coroutine taking no parameters which returns an object
        """
        self._object = None
        self._loader = loader

    def __getattribute__(self, attr):
        if attr in (['_object', '_loader', '__repr__', 'load', '__class__'] + type(self)._attributes):
            return object.__getattribute__(self, attr)
        else:
            if object.__getattribute__(self, '_object') is None:
                raise AsyncLazyLoaderUnloadedError(
                    "A call to {} was made on an object that hasn't been loaded".format(attr)
                )
            return getattr(object.__getattribute__(self, '_object'), attr)

    def __repr__(self):
        if object.__getattribute__(self, '_object') is None:
            return object.__repr__(self)
        else:
            return repr(object.__getattribute__(self, '_object'))

    def __setattr__(self, attr, value):
        if attr in ['_object', '_loader'] + type(self)._attributes:
            return object.__setattr__(self, attr, value)
        else:
            if object.__getattribute__(self, '_object') is None:
                raise AsyncLazyLoaderUnloadedError(
                    "A call to set {} was made on an object that hasn't been loaded".format(attr)
                )
            return setattr(object.__getattribute__(self, '_object'), attr, value)

    async def load(self):
        """Await this coroutine to load the actual object"""
        _loader = object.__getattribute__(self, "_loader")
        object.__setattr__(self, "_object", await _loader())


class AsyncIOBytes (AsyncLazyLoader, Sequence):
    """A Bytes-like object that is backed by a seekable Asynchronous IO stream and can be loaded asynchronously by
    awaiting its load coroutine.
    """

    _attributes = ['_istream', '_start', '_length', '__len__']

    def __init__(self, istream, start, length):
        """
        :param istream: An instance of an asynchronous seekable readable
        :param start: The value to pass to istream.seek to get to the start of this data
        :param start: The length of the data
        """
        async def __loadbytes():
            loc = await self._istream.tell()
            try:
                await self._istream.seek(self._start)
                _bytes = await self._istream.read(self._length)
            finally:
                await self._istream.seek(loc)
            return _bytes

        AsyncLazyLoader.__init__(self, __loadbytes)
        self._istream = istream
        self._start = start
        self._length = length

    def __len__(self):
        if self._object is None:
            return self._length
        else:
            return len(self._object)

    def __repr__(self):
        if self._object is None:
            return "AsyncIOBytes({!r}, {!r}, {!r})".format(self._istream, self._start, self._length)
        else:
            return repr(self._object)

    def __getitem__(self, *args, **kwargs):
        return self.__getattribute__('__getitem__')(*args, **kwargs)
