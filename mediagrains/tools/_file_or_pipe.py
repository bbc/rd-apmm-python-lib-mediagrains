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
"""Utility function to open a file or a pipe"""
import typing
from io import BufferedIOBase

import sys
from contextlib import contextmanager


class InputStreamWrapper(BufferedIOBase):
    def __init__(self, fp: typing.IO[bytes]):
        self._file = fp
        self._pos = 0

    def tell(self) -> int:
        return self._pos

    def read(self, size=-1) -> bytes:
        out = b""
        if size == -1:
            out = self._file.read(-1)
        else:
            s = size
            while len(out) < size:
                b = self._file.read(s)
                if len(b) == 0:
                    raise EOFError
                s -= len(b)
                out += b

        self._pos += len(out)
        return out

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            offset = offset - self._pos
        elif whence == 2:
            raise NotImplementedError("Cannot seek relative to the end of a stream")

        if offset < 0:
            raise NotImplementedError("Cannot seek backwards in a stream")
        if offset > 0:
            self._file.read(offset)
        self._pos += offset
        return self._pos


@contextmanager
def file_or_pipe(file_or_pipe: str, mode: str) -> typing.Iterator[typing.IO[bytes]]:
    """Context manager to open a file or stdin/stdout for binary operations

    :param file_or_pipe: Name of file to open, or "-" to indicate a pipe
    :param mode: Mode in which to open the given file or pipe - used directly for files and to detect direction of
                 of pipes. Must be one of "rb" or "wb"
    """
    if file_or_pipe == "-":
        if "w" in mode:
            yield sys.stdout.buffer
        else:
            yield typing.cast(typing.IO[bytes], InputStreamWrapper(sys.stdin.buffer))
    else:
        with open(file_or_pipe, mode) as fp:
            yield fp
