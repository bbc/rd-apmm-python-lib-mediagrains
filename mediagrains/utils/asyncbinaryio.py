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
An abstract base class for asynchronous equivalent of io.RawIOBase

I haven't included all of the machinary in that other class, it seems more logical to simplify the
interface a little.
"""

from abc import ABCMeta, abstractmethod
from io import SEEK_SET, SEEK_CUR

from typing import Type, Union, Optional, IO, cast
from io import RawIOBase


class OpenAsyncBinaryIO(metaclass=ABCMeta):
    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            return await self.readall()
        else:
            while True:
                b = bytearray(size)
                s = await self.readinto(b)
                if s is None:
                    continue
                if s < size:
                    raise EOFError
                return bytes(b)

    @abstractmethod
    async def readinto(self, b: bytearray) -> Union[int, None]: ...

    @abstractmethod
    async def readall(self) -> bytes: ...

    @abstractmethod
    async def write(self, b: bytes) -> Optional[int]: ...

    @abstractmethod
    async def truncate(self, s: Optional[int] = None) -> int: ...

    @abstractmethod
    def tell(self) -> int: ...

    @abstractmethod
    def seek(self, offset: int, whence: int = SEEK_SET): ...

    @abstractmethod
    def seekable(self) -> bool: ...

    @abstractmethod
    def readable(self) -> bool: ...

    @abstractmethod
    def writable(self) -> bool: ...

    async def __open__(self) -> None:
        "This coroutine should include any code that is to be run when the io stream is opened"
        pass

    async def __close__(self) -> None:
        "This coroutine should include any code that is to be run when the io stream is closed"
        pass


class AsyncBinaryIO:
    def __init__(self, cls: Type[OpenAsyncBinaryIO], *args, **kwargs):
        self._inst = cls(*args, **kwargs)  # type: ignore

    async def __aenter__(self) -> OpenAsyncBinaryIO:
        await self._inst.__open__()
        return self._inst

    async def __aexit__(self, *args, **kwargs) -> None:
        await self._inst.__close__()


class OpenAsyncBytesIO(OpenAsyncBinaryIO):
    def __init__(self, b: bytes):
        self._buffer = bytearray(b)
        self._pos = 0
        self._len = len(b)

    async def __open__(self) -> None:
        "This coroutine should include any code that is to be run when the io stream is opened"
        self._pos = 0

    async def readinto(self, b: bytearray) -> int:
        length = min(self._len - self._pos, len(b))
        if length > 0:
            b[:length] = self._buffer[self._pos:self._pos + length]
            self._pos += length
            return length
        else:
            return 0

    async def readall(self) -> bytes:
        if self._pos >= 0 and self._pos < self._len:
            return bytes(self._buffer[self._pos:self._len])
        else:
            return bytes()

    async def write(self, b: bytes) -> int:
        if self._pos < 0:
            return 0

        if self._pos + len(b) > len(self._buffer):
            newbuf = bytearray(max(self._pos + len(b), 2*len(self._buffer)))
            newbuf[:self._len] = self._buffer[:self._len]
            self._buffer = newbuf

        length = len(b)
        self._buffer[self._pos:self._pos + length] = b[:length]
        self._pos += length
        self._len = max(self._pos, self._len)
        return length

    async def truncate(self, size: Optional[int] = None) -> int:
        if size is not None:
            self._len = size
        else:
            self._len = max(self._pos, 0)

        return self._len

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = SEEK_SET):
        if whence == SEEK_SET:
            self._pos = offset
        elif whence == SEEK_CUR:
            self._pos += offset
        else:
            self._pos = self._len + offset

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def getbuffer(self) -> bytearray:
        return self._buffer[:self._len]

    def value(self) -> bytes:
        return bytes(self._buffer[:self._len])


class AsyncBytesIO(AsyncBinaryIO):
    def __init__(self, b: bytes = b""):
        super().__init__(cls=OpenAsyncBytesIO, b=b)
        self._inst: OpenAsyncBytesIO

    def getbuffer(self) -> bytearray:
        return self._inst.getbuffer()

    def value(self) -> bytes:
        return self._inst.value()


class OpenAsyncFileWrapper(OpenAsyncBinaryIO):
    def __init__(self, fp: IO[bytes]):
        self.fp = cast(RawIOBase, fp)

    async def __open__(self) -> None:
        # self.fp.__enter__()
        pass

    async def __close__(self) -> None:
        # self.fp.__exit__(None, None, None)
        pass

    async def read(self, s: int = -1) -> bytes:
        while True:
            r = self.fp.read(s)
            if r is not None:
                return r

    async def readinto(self, b: bytearray) -> Optional[int]:
        return self.fp.readinto(b)

    async def readall(self) -> bytes:
        return self.fp.readall()

    async def write(self, b: bytes) -> Optional[int]:
        return self.fp.write(b)

    async def truncate(self, size: Optional[int] = None) -> int:
        return self.fp.truncate(size)

    def tell(self) -> int:
        return self.fp.tell()

    def seek(self, offset: int, whence: int = SEEK_SET):
        return self.fp.seek(offset, whence)

    def seekable(self) -> bool:
        return self.fp.seekable()

    def readable(self) -> bool:
        return self.fp.readable()

    def writable(self) -> bool:
        return self.fp.writable()

    def getsync(self) -> IO[bytes]:
        return cast(IO[bytes], self.fp)


class AsyncFileWrapper(AsyncBinaryIO):
    def __init__(self, fp: IO[bytes]):
        super().__init__(cls=OpenAsyncFileWrapper, fp=fp)
        self._inst: OpenAsyncFileWrapper
        self.fp = fp
