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
from io import SEEK_SET, SEEK_CUR, BytesIO

from typing import Type, Union, Optional, IO, cast, TypeVar, Callable, Coroutine
from io import RawIOBase, UnsupportedOperation

from asyncio import StreamReader, StreamWriter
import asyncio
from functools import wraps

from deprecated import deprecated


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

    def seekable_forwards(self) -> bool:
        return self.seekable()

    def seekable_backwards(self) -> bool:
        return self.seekable()

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


T = TypeVar("T")


def wrap_in_executor(f: Callable[..., T]) -> Callable[..., Coroutine[None, None, T]]:
    @wraps(f)
    async def __inner(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(None, lambda: f(*args, **kwargs))
    return __inner


class OpenAsyncBytesIO(OpenAsyncBinaryIO):
    def __init__(self, b: bytes):
        self._buffer = bytearray(b)
        self._pos = 0
        self._len = len(b)

    async def __open__(self) -> None:
        "This coroutine should include any code that is to be run when the io stream is opened"
        self._pos = 0

    @wrap_in_executor
    def readinto(self, b: bytearray) -> int:
        length = min(self._len - self._pos, len(b))
        if length > 0:
            b[:length] = self._buffer[self._pos:self._pos + length]
            self._pos += length
            return length
        else:
            return 0

    @wrap_in_executor
    def readall(self) -> bytes:
        if self._pos >= 0 and self._pos < self._len:
            return bytes(self._buffer[self._pos:self._len])
        else:
            return bytes()

    @wrap_in_executor
    def write(self, b: bytes) -> int:
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

    @deprecated(version="2.8.0", reason="Use getvalue instead to be more consistent with the standard library")
    def value(self) -> bytes:
        return self.getvalue()

    def getvalue(self) -> bytes:
        return bytes(self._buffer[:self._len])


class AsyncBytesIO(AsyncBinaryIO):
    def __init__(self, b: bytes = b""):
        super().__init__(cls=OpenAsyncBytesIO, b=b)
        self._inst: OpenAsyncBytesIO

    def getbuffer(self) -> bytearray:
        return self._inst.getbuffer()

    def value(self) -> bytes:
        return self.getvalue()

    def getvalue(self) -> bytes:
        return self._inst.getvalue()


class OpenAsyncFileWrapper(OpenAsyncBinaryIO):
    def __init__(self, fp: IO[bytes]):
        self.fp = cast(RawIOBase, fp)

    async def __open__(self) -> None:
        pass

    async def __close__(self) -> None:
        pass

    @wrap_in_executor
    def read(self, s: int = -1) -> bytes:
        while True:
            r = self.fp.read(s)
            if r is not None:
                return r

    async def readinto(self, b: bytearray) -> Optional[int]:
        return await wrap_in_executor(self.fp.readinto)(b)

    async def readall(self) -> bytes:
        return await wrap_in_executor(self.fp.readall)()

    async def write(self, b: bytes) -> Optional[int]:
        return await wrap_in_executor(self.fp.write)(b)

    async def truncate(self, size: Optional[int] = None) -> int:
        return await wrap_in_executor(self.fp.truncate)(size)

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


class OpenAsyncBytesIOWrapper(OpenAsyncBinaryIO):
    def __init__(self, fp: BytesIO):
        self.fp = cast(RawIOBase, fp)

    async def __open__(self) -> None:
        pass

    async def __close__(self) -> None:
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


class AsyncBytesIOWrapper(AsyncBinaryIO):
    def __init__(self, fp: BytesIO):
        super().__init__(cls=OpenAsyncBytesIOWrapper, fp=fp)
        self._inst: OpenAsyncBytesIOWrapper
        self.fp = fp


class OpenAsyncStreamWrapper(OpenAsyncBinaryIO):
    def __init__(self, reader: Optional[StreamReader] = None, writer: Optional[StreamWriter] = None):
        self.reader = reader
        self.writer = writer
        self._pos = 0
        self._next_pos = 0

    async def __open__(self) -> None:
        self._pos = 0
        self._next_pos = 0

    async def __close__(self) -> None:
        if self.writer is not None:
            self.writer.close()

    async def _align_pos(self):
        if self._next_pos > self._pos:
            if self.reader is not None:
                await self.reader.read(self._next_pos - self._pos)
            if self.writer is not None:
                self.writer.write(bytes(self._next_pos - self._pos))
            self._pos = self._next_pos

    async def read(self, s: int = -1) -> bytes:
        if self.reader is None:
            raise UnsupportedOperation("Attempted to read from an output stream")
        await self._align_pos()
        d = await self.reader.read(s)
        self._pos += len(d)
        return d

    async def readinto(self, b: bytearray) -> Optional[int]:
        if self.reader is None:
            raise UnsupportedOperation("Attempted to read from an output stream")
        await self._align_pos()
        d = await self.reader.read(len(b))
        if d is None:
            return 0
        else:
            b[:len(d)] = d
            self._pos += len(d)
            return len(d)

    async def readall(self) -> bytes:
        d = await self.read()
        self._pos += len(d)
        return d

    async def write(self, b: bytes) -> Optional[int]:
        if self.writer is None:
            raise UnsupportedOperation("Attempted to write to an input stream")
        await self._align_pos()
        self.writer.write(b)
        await self.writer.drain()
        self._pos += len(b)
        return len(b)

    async def truncate(self, size: Optional[int] = None) -> int:
        raise UnsupportedOperation("Cannot truncate a network stream")

    def tell(self) -> int:
        if self._next_pos > self._pos:
            # use self._next_pos as the base position as self._pos has not been aligned after a seek
            return self._next_pos
        else:
            return self._pos

    def seek(self, offset: int, whence: int = SEEK_SET):
        if self._next_pos > self._pos:
            # use self._next_pos as the base position as self._pos has not been aligned after a seek
            next_pos = self._next_pos
        else:
            next_pos = self._pos

        if whence == SEEK_SET:
            next_pos = offset
        elif whence == SEEK_CUR:
            next_pos += offset
        else:
            raise UnsupportedOperation("Cannot seek backwards")
        if next_pos < self._pos:
            raise UnsupportedOperation("Cannot seek backwards")
        self._next_pos = next_pos
        return self._next_pos

    def seekable(self) -> bool:
        return False

    def readable(self) -> bool:
        return (self.reader is not None)

    def writable(self) -> bool:
        return (self.writer is not None)

    def seekable_backwards(self) -> bool:
        return False

    def seekable_forwards(self) -> bool:
        return True

    def getstream(self):
        return (self.reader, self.writer)


class AsyncStreamWrapper(AsyncBinaryIO):
    def __init__(self, reader: Optional[StreamReader] = None, writer: Optional[StreamWriter] = None):
        super().__init__(cls=OpenAsyncStreamWrapper, reader=reader, writer=writer)
        self._inst: OpenAsyncStreamWrapper
        self.reader = reader
        self.writer = writer

    def getstream(self):
        return (self.reader, self.writer)
