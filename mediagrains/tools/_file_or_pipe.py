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

import sys
from contextlib import contextmanager


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
            yield sys.stdin.buffer
    else:
        with open(file_or_pipe, mode) as fp:
            yield fp
