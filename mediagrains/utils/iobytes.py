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
A simple wrapper class IOBytes which is a conceptual inverse to the standard
library's io.BytesIO, taking an io stream and wrapping it to appear as a
bytes object, lazily loading as necessary.
"""

from collections.abc import Sequence
from typing import List

__all__ = ["IOBytes"]


class LazyLoader (object):
    """An object that will be loaded lazily as needed.

    In most cases this class should be subclassed to make actually useful classes, but technically it's not
    an abstract base class because it *can* be used directly if needed.

    The constructor takes a callable which takes no parameters and returns an object as its only parameter.

    Upon construction this "loader" callable is not called, but the first call to any method or access to any attribute
    of the LazyLoader object will cause the loader to be called, its return value stored inside the object, and the
    attribute/method/etc ... of that object with the same name to be returned instead. All future access is
    transparently passed through to the stored object.
    """

    _attributes: List[str] = []

    def __init__(self, loader):
        """
        :param loader: a callable taking no parameters which returns an object
        """
        self._object = None
        self._loader = loader

    def __getattribute__(self, attr):
        if attr in (['_object', '_loader', '__repr__', '__class__'] + type(self)._attributes):
            return object.__getattribute__(self, attr)
        else:
            if object.__getattribute__(self, '_object') is None:
                self._object = object.__getattribute__(self, '_loader')()
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
                self._object = object.__getattribute__(self, '_loader')()
            return setattr(object.__getattribute__(self, '_object'), attr, value)

    # In python2.7 some special methods may bypass __getattribute__, so need to be specifically redefined
    def __lt__(self, *args, **kwargs):
        return self.__getattribute__('__lt__')(*args, **kwargs)

    def __le__(self, *args, **kwargs):
        return self.__getattribute__('__le__')(*args, **kwargs)

    def __gt__(self, *args, **kwargs):
        return self.__getattribute__('__gt__')(*args, **kwargs)

    def __ge__(self, *args, **kwargs):
        return self.__getattribute__('__ge__')(*args, **kwargs)

    def __eq__(self, *args, **kwargs):
        return self.__getattribute__('__eq__')(*args, **kwargs)

    def __ne__(self, *args, **kwargs):
        return self.__getattribute__('__ne__')(*args, **kwargs)

    def __cmp__(self, *args, **kwargs):
        return self.__getattribute__('__cmp__')(*args, **kwargs)

    def __nonzero__(self, *args, **kwargs):
        return self.__getattribute__('__nonzero__')(*args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.__getattribute__('__contains__')(*args, **kwargs)

    def __hash__(self, *args, **kwargs):
        return self.__getattribute__('__hash__')(*args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        return self.__getattribute__('__setitem__')(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.__getattribute__('__getitem__')(*args, **kwargs)

    def __str__(self, *args, **kwargs):
        return self.__getattribute__('__str__')(*args, **kwargs)

    def __unicode__(self, *args, **kwargs):
        return self.__getattribute__('__unicode__')(*args, **kwargs)


class IOBytes (LazyLoader, Sequence):
    """An almost Bytes-like object that is backed by a seekable IO stream.

    This object can be used in almost all places where a bytes-like object is demanded, however not quite all.
    To pass into a method that directly uses the C buffer protocol (such as struct.decode) this object is not good
    enough. In that case a real bytes object can be created by passing this object as the sole parameter of the
    constructor "bytes".

    Current behaviour is to read the whole of the data segment into a bytes-like object, but *only* the
    first time the data actually needs to be accessed. Notably calls to __len__ and __repr__ do not cause the
    data to be read from the stream. The location of the stream pointer is restored to its previous location
    after this read so it should be transparent."""

    _attributes = ['_istream', '_start', '_length', '__len__']

    def __init__(self, istream, start, length):
        """
        :param istream: An instance of a seekable IOBase
        :param start: The value to pass to istream.seek to get to the start of this data
        :param start: The length of the data
        """
        def __loadbytes():
            loc = self._istream.tell()
            try:
                self._istream.seek(self._start)
                _bytes = self._istream.read(self._length)
            finally:
                self._istream.seek(loc)
            return _bytes

        LazyLoader.__init__(self, __loadbytes)
        self._istream = istream
        self._start = start
        self._length = length

    def __bytes__(self):
        if self._object is None:
            self._object = object.__getattribute__(self, '_loader')()
        return self._object

    def __len__(self):
        if self._object is None:
            return self._length
        else:
            return len(self._object)

    def __repr__(self):
        if self._object is None:
            return "IOBytes({!r}, {!r}, {!r})".format(self._istream, self._start, self._length)
        else:
            return repr(self._object)
