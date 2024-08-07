#
# Copyright 2018 British Broadcasting Corporation
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
A library for deserialising GSF files, either from string buffers or file
objects.
See https://github.com/bbc/rd-apmm-python-lib-mediagrains/blob/main/gsf_docs/gsf.md
for documentation of the GSF format.
"""

from .grains import Grain, GrainFactory
from uuid import UUID, uuid1
from datetime import datetime, timezone
from io import BytesIO, RawIOBase, BufferedIOBase
from mediatimestamp.immutable import Timestamp
from fractions import Fraction
from frozendict import frozendict
from .utils import IOBytes
from os import SEEK_SET, SEEK_CUR
import warnings

from inspect import isawaitable

from typing import (
    Optional,
    Iterable,
    Tuple,
    List,
    Dict,
    Mapping,
    cast,
    Union,
    Type,
    IO,
    Sequence,
    AsyncIterable,
    Awaitable,
    overload,
    NamedTuple)
from typing_extensions import TypedDict
from .typing import GrainMetadataDict, RationalTypes, ParseGrainType

from .grains import VideoGrain, EventGrain, AudioGrain, CodedAudioGrain, CodedVideoGrain

from .utils.asyncbinaryio import AsyncBinaryIO, OpenAsyncBinaryIO, AsyncFileWrapper, OpenAsyncFileWrapper

from contextlib import contextmanager

from deprecated import deprecated

from enum import Enum


__all__ = ["GSFDecoder", "load", "loads", "GSFError", "GSFDecodeError",
           "GSFDecodeBadFileTypeError", "GSFDecodeBadVersionError",
           "GSFEncoder", "dump", "dumps", "GSFEncodeError",
           "GSFEncodeAddToActiveDump"]


@contextmanager
def no_deprecation_warnings():
    with warnings.catch_warnings(record=True) as warns:
        yield

    for w in warns:
        if w.category != DeprecationWarning:
            warnings.showwarning(w.message, w.category, w.filename, w.lineno)


GSFFileHeaderDict = dict


def loads(s: bytes,
          cls: Optional[Type["GSFDecoder"]] = None,
          parse_grain: Optional[ParseGrainType] = None,
          **kwargs) -> Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]:
    """Deserialise a GSF file from a string (or similar) into python,
    returns a pair of (head, segments) where head is a python dict
    containing general metadata from the file, and segments is a dictionary
    mapping numeric segment ids to lists of Grain objects.

    If you wish to use a custom GSFDecoder subclass pass it as cls, if you
    wish to use a custom Grain constructor pass it as parse_grain. The
    defaults are GSFDecoder and Grain. Extra kwargs will be passed to the
    decoder constructor."""
    if cls is None:
        cls = GSFDecoder
    if parse_grain is None:
        parse_grain = GrainFactory

    return load(BytesIO(s), cls=cls, parse_grain=parse_grain)


@overload
def load(fp: IO[bytes],
         cls: Optional[Type["GSFDecoder"]] = None,
         parse_grain: Optional[ParseGrainType] = None,
         **kwargs) -> Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]: ...


@overload
def load(fp: AsyncBinaryIO,
         cls: Optional[Type["GSFDecoder"]] = None,
         parse_grain: Optional[ParseGrainType] = None,
         **kwargs) -> Awaitable[Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]]: ...


def load(fp,
         cls=None,
         parse_grain=None,
         **kwargs):
    """Deserialise a GSF file from a file object (or similar) into python,
    returns a pair of (head, segments) where head is a python dict
    containing general metadata from the file, and segments is a dictionary
    mapping numeric segment ids to lists of Grain objects.

    If an asynchronous file object is provided then return an awaitable that
    will do the above.

    If you wish to use a custom GSFDecoder subclass pass it as cls, if you
    wish to use a custom Grain constructor pass it as parse_grain. The
    defaults are GSFDecoder and Grain. Extra kwargs will be passed to the
    decoder constructor."""
    if cls is None:
        cls = GSFDecoder
    if parse_grain is None:
        parse_grain = GrainFactory

    if isinstance(fp, AsyncBinaryIO):
        return cls(file_data=fp, parse_grain=parse_grain, **kwargs)._asynchronously_decode()
    else:
        return cls(file_data=fp, parse_grain=parse_grain, **kwargs)._synchronously_decode()


def dump(grains: Iterable[Grain],
         fp: IO[bytes],
         cls: Optional[Type["GSFEncoder"]] = None,
         segment_tags: Optional[Iterable[Tuple[str, str]]] = None,
         **kwargs) -> None:
    """Serialise a series of grains into a GSF file.

    :param grains an iterable of grain objects
    :param fp a ByteIO-like object to write to
    :param segment_tags a list of pairs of strings to use as tags for the segment created
    :param cls the class to use for encoding, GSFEncoder is the default

    other keyword arguments will be fed to the class constructor.

    This method will serialise the grains in a single segment."""
    if cls is None:
        cls = GSFEncoder

    with cls(fp, **kwargs) as enc:
        seg = enc.add_segment(tags=segment_tags)
        seg.add_grains(grains)


def dumps(grains: Iterable[Grain],
          cls: Optional[Type["GSFEncoder"]] = None,
          segment_tags: Optional[Iterable[Tuple[str, str]]] = None,
          **kwargs) -> bytes:
    """Serialise a series of grains into a new bytes object.

    :param grains an iterable of grain objects
    :param fp a ByteIO-like object to write to
    :param segment_tags a list of pairs of strings to use as tags for the segment created
    :param cls the class to use for encoding, GSFEncoder is the default

    other keyword arguments will be fed to the class constructor.

    This method will serialise the grains in a single segment."""
    b = BytesIO()
    dump(grains, b, cls=cls, segment_tags=segment_tags, **kwargs)
    return b.getvalue()


class GSFError(Exception):
    """A generic GSF error, all other GSF exceptions inherit from it."""
    pass


class GSFDecodeError(GSFError):
    """A generic GSF Decoder error, all other GSF Decodrr exceptions inherit from it.

    properties:

    offset
        The offset from the start of the file at which the bad data is located

    length
        The length of the bad data"""
    def __init__(self, msg, i, length=None):
        super(GSFDecodeError, self).__init__(msg)
        self.offset = i
        self.length = length


class GSFDecodeBadFileTypeError(GSFDecodeError):
    """The file type was not GSF.
    properties:

    filetype
        The file type string"""
    def __init__(self, msg, i, filetype):
        super(GSFDecodeBadFileTypeError, self).__init__(msg, i, 8)
        self.filetype = filetype


class GSFDecodeBadVersionError(GSFDecodeError):
    """The version was unsupported

    properties:

    major
        The major version detected

    minor
        The minor version detected"""
    def __init__(self, msg, i, major, minor):
        super(GSFDecodeBadVersionError, self).__init__(msg, i, 8)
        self.major = major
        self.minor = minor


class AsyncGSFBlock():
    """A single block in a GSF file

    Has methods to read various types from the block.
    Can also be used as an async context manager, in which case it will automatically decode the block tag and size,
    exposed by the `tag` and `size` attributes.
    """
    def __init__(
        self,
        file_data: Union[OpenAsyncBinaryIO, "AsyncGSFBlock"],
        want_tag: Optional[str] = None,
        raise_on_wrong_tag: bool = False
    ):
        """Constructor. Records the start byte of the block in `block_start`

        :param file_data: An instance of io.BufferedReader or AsyncGSFBlock positioned at the start of the block
        :param want_tag: If set to a tag string, and in a context manager, skip any block without that tag
        :param raise_on_wrong_tag: Set to True to raise a GSFDecodeError if the next block isn't `want_tag`
        """
        self.file_data: OpenAsyncBinaryIO
        if isinstance(file_data, AsyncGSFBlock):
            block = file_data
            self.file_data = block.file_data
        else:
            self.file_data = file_data
        self.want_tag = want_tag
        self.raise_on_wrong_tag = raise_on_wrong_tag

        self.size: Optional[int] = None
        self.block_start = self.file_data.tell()  # In binary mode, this should always be in bytes

    async def __aenter__(self) -> "AsyncGSFBlock":
        """When used as a context manager, read block size and tag on entry

        - When entering a block, tag and size should be read
        - If tag doesn't decode, a GSFDecodeError should be raised
        - If want_tag was supplied to the constructor, skip blocks that don't have that tag
        - Unless raise_on_wrong_tag was also supplied, in which case raise

        :returns: Instance of GSFBlock
        :raises GSFDecodeError: If the block tag failed to decode as UTF-8, or an unwanted tag was found
        """
        assert self.file_data.tell() == self.block_start, "Can't enter context manager after the block start"

        while True:
            self.tag = await self.read_tag()

            if self.tag == "SSBB":
                # A concatenated file header
                grsg_tag = await self.read_tag()
                if grsg_tag != "grsg":
                    raise GSFDecodeError(
                        f"Expected grsg tag after SSBB but got {grsg_tag} at {self.block_start}",
                        self.block_start
                    )
                # Include just the grsg tag in this pseudo block
                self.size = 8
            else:
                self.size = await self.read_uint(4)

            if self.want_tag is None or self.tag == self.want_tag:
                return self
            elif self.tag != self.want_tag and self.raise_on_wrong_tag:
                raise GSFDecodeError("Wanted tag {} but got {} at {}".format(self.want_tag, self.tag, self.block_start),
                                     self.block_start)
            else:
                # If size is < 8 bytes then it is a special value, e.g. a terminator grai.
                # If the size is special value then the actual size is 8
                actual_size = max(8, self.size)

                self.file_data.seek(self.block_start + actual_size, SEEK_SET)
                self.block_start = self.file_data.tell()

                self.size = None
                self.tag = ""

    async def __aexit__(self, *args):
        """When used as a context manager, exiting context should seek to the block end"""
        try:
            if self.size is not None:
                # If size is < 8 bytes then it is a special value, e.g. a terminator grai.
                # If the size is special value then the actual size is 8
                actual_size = max(8, self.size)
            else:
                actual_size = 0
            self.file_data.seek(self.block_start + actual_size, SEEK_SET)
        except Exception:
            pass

    def has_child_block(self, strict_blocks=True):
        """Checks if there is space for another child block in this block

        Returns true if there is space for another child block (i.e. >= 8 bytes) in this block.
        If strict_blocks=True, this block only contains other blocks rather than any other data. As a result, if there
        are bytes left, but not enough for another block, raise a GSFDecodeError.
        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :returns: True if there is spaces for another block
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        assert self.size is not None, "has_child_block() only works in a context manager"

        bytes_remaining = self.get_remaining()
        if bytes_remaining >= 8:
            return True
        elif bytes_remaining != 0 and strict_blocks:
            position = self.file_data.tell()
            raise GSFDecodeError("Found a partial block (or parent too small) in '{}' at {}".format(self.tag, position),
                                 position)
        else:
            return False

    async def child_blocks(self, strict_blocks=True):
        """Generator for each child block - each yielded block sits within the context manager

        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :yields: GSFBlock for child (already acting as a context manager)
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        while self.has_child_block(strict_blocks=strict_blocks):
            async with AsyncGSFBlock(self.file_data) as child_block:
                yield child_block

    def get_remaining(self):
        """Get the number of bytes left in this block

        Only works in a context manager, will raise an AssertionError if not

        :returns: Number of bytes left in the block
        """
        assert self.size is not None, "get_remaining() only works in a context manager"
        return (self.block_start + self.size) - self.file_data.tell()

    async def read_remaining_block(self) -> "SyncGSFBlock":
        """Reads the remaining data into a SyncGSFBlock
        """
        assert self.size is not None, "read_remaining_block() only works in a context manager"

        start = self.file_data.tell()

        bytes_remaining = self.get_remaining()
        if bytes_remaining > 0:
            buffer = await self.file_data.read(bytes_remaining)
        else:
            buffer = bytes()

        block = SyncGSFBlock(BytesIO(buffer), file_data_start=start)

        # Copy the state that would be set when entering the context manager
        block.size = self.size
        block.tag = self.tag
        block.block_start = self.block_start

        return block

    async def read_tag(self) -> str:
        """Read a 4 character tag

        :returns: Tag string
        :raises EOFError: If there are fewer than 4 bytes left in the source
        """
        return await self.read_string(4)

    async def read_uint(self, length) -> int:
        """Read an unsigned integer of length `length`

        :param length: Number of bytes used to store the integer
        :returns: Unsigned integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = 0
        uint_bytes = await self.file_data.read(length)

        if len(uint_bytes) != length:
            raise EOFError("Unable to read enough bytes from source")

        for n in range(0, length):
            r += (uint_bytes[n] << (n*8))
        return r

    async def read_string(self, length: int) -> str:
        """Read a fixed-length string, treating it as UTF-8

        :param length: Number of bytes in the string
        :returns: String
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        string_data = await self.file_data.read(length)
        if (len(string_data) != length):
            raise EOFError("Unable to read enough bytes from source")

        try:
            string = string_data.decode(encoding='utf-8').rstrip('\x00')
            if not string or string[0] == '\x00':
                return ""
            return string
        except UnicodeDecodeError:
            raise GSFDecodeError(
                f"Failed to decode bytes in block starting at {self.block_start} to a valid string",
                self.block_start
            )


class SyncGSFBlock():
    """A single block in a GSF file

    Has methods to read various types from the block.
    Can also be used as a context manager, in which case it will automatically decode the block tag and size, exposed
    by the `tag` and `size` attributes.
    """
    def __init__(
        self,
        file_data: Union[IO[bytes], "SyncGSFBlock"],
        file_data_start: int = 0,
        want_tag: Optional[str] = None,
        raise_on_wrong_tag: bool = False
    ):
        """Constructor. Records the start byte of the block in `block_start`

        :param file_data: An instance of io.BufferedReader or SyncGSFBlock positioned at the start of this block
        :param file_data_start: Base file position of first byte in file_data. Ignored if file_data is a SyncGSFBlock
        :param want_tag: If set to a tag string, and in a context manager, skip any block without that tag
        :param raise_on_wrong_tag: Set to True to raise a GSFDecodeError if the next block isn't `want_tag`
        """
        self.file_data: IO[bytes]
        self.file_data_start: int
        if isinstance(file_data, SyncGSFBlock):
            block = file_data
            self.file_data = block.file_data
            self.file_data_start = block.file_data_start
        else:
            self.file_data = cast(IO[bytes], file_data)
            self.file_data_start = file_data_start
        self.want_tag = want_tag
        self.raise_on_wrong_tag = raise_on_wrong_tag

        self.size: Optional[int] = None
        self.block_start = self._base_file_tell()  # In binary mode, this should always be in bytes

    def _base_file_tell(self) -> int:
        """Return the position in the base file using the base file offset self.file_data_start"""
        return self.file_data_start + self.file_data.tell()

    def __enter__(self) -> "SyncGSFBlock":
        """When used as a context manager, read block size and tag on entry

        - When entering a block, tag and size should be read
        - If tag doesn't decode, a GSFDecodeError should be raised
        - If want_tag was supplied to the constructor, skip blocks that don't have that tag
        - Unless raise_on_wrong_tag was also supplied, in which case raise

        :returns: Instance of GSFBlock
        :raises GSFDecodeError: If the block tag failed to decode as UTF-8, or an unwanted tag was found
        """
        assert self._base_file_tell() == self.block_start, "Can't enter context manager after the block start"

        # NOTE: Ensure that changes to the state set here is also changed in read_remaining_block
        # in SyncGSFBlock and AsyncGSFBlock
        while True:
            self.tag = self.read_tag()

            if self.tag == "SSBB":
                # A concatenated file header
                grsg_tag = self.read_tag()
                if grsg_tag != "grsg":
                    raise GSFDecodeError(
                        f"Expected grsg tag after SSBB but got {grsg_tag} at {self.block_start}",
                        self.block_start
                    )
                # Include just the grsg tag in this pseudo block
                self.size = 8
            else:
                self.size = self.read_uint(4)

            if self.want_tag is None or self.tag == self.want_tag:
                return self
            elif self.tag != self.want_tag and self.raise_on_wrong_tag:
                raise GSFDecodeError("Wanted tag {} but got {} at {}".format(self.want_tag, self.tag, self.block_start),
                                     self.block_start)
            else:
                # If size is < 8 bytes then it is a special value, e.g. a terminator grai.
                # If the size is special value then the actual size is 8
                actual_size = max(8, self.size)

                self.file_data.seek(self.block_start + actual_size - self.file_data_start, SEEK_SET)
                self.block_start = self._base_file_tell()

                self.size = None
                self.tag = ""

    def __exit__(self, *args):
        """When used as a context manager, exiting context should seek to the block end"""
        try:
            if self.size is not None:
                # If size is < 8 bytes then it is a special value, e.g. a terminator grai.
                # If the size is special value then the actual size is 8
                actual_size = max(8, self.size)
            else:
                actual_size = 0
            self.file_data.seek(self.block_start + actual_size - self.file_data_start, SEEK_SET)
        except Exception:
            pass

    def has_child_block(self, strict_blocks=True):
        """Checks if there is space for another child block in this block

        Returns true if there is space for another child block (i.e. >= 8 bytes) in this block.
        If strict_blocks=True, this block only contains other blocks rather than any other data. As a result, if there
        are bytes left, but not enough for another block, raise a GSFDecodeError.
        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :returns: True if there is spaces for another block
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        assert self.size is not None, "has_child_block() only works in a context manager"

        bytes_remaining = self.get_remaining()
        if bytes_remaining >= 8:
            return True
        elif bytes_remaining != 0 and strict_blocks:
            position = self._base_file_tell()
            raise GSFDecodeError("Found a partial block (or parent too small) in '{}' at {}".format(self.tag, position),
                                 position)
        else:
            return False

    def child_blocks(self, strict_blocks=True):
        """Generator for each child block - each yielded block sits within the context manager

        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :yields: GSFBlock for child (already acting as a context manager)
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        while self.has_child_block(strict_blocks=strict_blocks):
            with SyncGSFBlock(self) as child_block:
                yield child_block

    def get_remaining(self):
        """Get the number of bytes left in this block

        Only works in a context manager, will raise an AssertionError if not

        :returns: Number of bytes left in the block
        """
        assert self.size is not None, "get_remaining() only works in a context manager"
        return (self.block_start + self.size) - (self.file_data_start + self.file_data.tell())

    def read_remaining_block(self) -> "SyncGSFBlock":
        """Reads the remaining data into a SyncGSFBlock
        """
        assert self.size is not None, "read_remaining_block() only works in a context manager"

        start = self._base_file_tell()

        bytes_remaining = self.get_remaining()
        if bytes_remaining > 0:
            buffer = self.file_data.read(bytes_remaining)
        else:
            buffer = bytes()

        block = SyncGSFBlock(BytesIO(buffer), file_data_start=start)

        # Copy the state that would be set when entering the context manager
        block.size = self.size
        block.tag = self.tag
        block.block_start = self.block_start

        return block

    def read_tag(self) -> str:
        """Read a 4 character tag

        :returns: Tag string
        :raises EOFError: If there are fewer than 4 bytes left in the source
        """
        return self.read_string(4)

    def read_uint(self, length) -> int:
        """Read an unsigned integer of length `length`

        :param length: Number of bytes used to store the integer
        :returns: Unsigned integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = 0
        uint_bytes = self.file_data.read(length)

        if len(uint_bytes) != length:
            raise EOFError("Unable to read enough bytes from source")

        for n in range(0, length):
            r += (uint_bytes[n] << (n*8))
        return r

    def read_bool(self):
        """Read a boolean value

        :returns: Boolean value
        :raises EOFError: If there are no more bytes left in the source"""
        n = self.read_uint(1)
        return (n != 0)

    def read_optional_bool(self):
        """Read an optional boolean value

        :returns: Boolean | None value
        :raises EOFError: If there are no more bytes left in the source"""
        n = self.read_uint(1)
        if n > 1:
            return None
        else:
            return (n != 0)

    def read_sint(self, length: int) -> int:
        """Read a 2's complement signed integer

        :param length: Number of bytes used to store the integer
        :returns: Signed integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = self.read_uint(length)
        if (r >> ((8*length) - 1)) == 1:
            r -= (1 << (8*length))
        return r

    def read_optional_sint(self, length: int, null_value: int) -> int | None:
        """Read an optional 2's complement signed integer

        :param length: Number of bytes used to store the integer
        :param null_value: Value that indicates it is null
        :returns: Signed integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = self.read_uint(length)
        if r == null_value:
            return None
        if (r >> ((8*length) - 1)) == 1:
            r -= (1 << (8*length))
        return r

    def read_string(self, length: int) -> str:
        """Read a fixed-length string, treating it as UTF-8

        :param length: Number of bytes in the string
        :returns: String
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        string_data = self.file_data.read(length)
        if (len(string_data) != length):
            raise EOFError("Unable to read enough bytes from source")

        try:
            string = string_data.decode(encoding='utf-8').rstrip('\x00')
            if not string or string[0] == '\x00':
                return ""
            return string
        except UnicodeDecodeError:
            raise GSFDecodeError(
                f"Failed to decode bytes in block starting at {self.block_start} to a valid string",
                self.block_start
            )

    def read_varstring(self) -> str:
        """Read a variable length string

        Reads a 2 byte uint to get the string length, then reads a string of that length

        :returns: String
        :raises EOFError: If there are too few bytes left in the source
        """
        length = self.read_uint(2)
        return self.read_string(length)

    def read_uuid(self) -> UUID:
        """Read a UUID

        :returns: UUID
        :raises EOFError: If there are fewer than l bytes left in the source
        """
        uuid_data = self.file_data.read(16)

        if (len(uuid_data) != 16):
            raise EOFError("Unable to read enough bytes from source")

        return UUID(bytes=uuid_data)

    def read_datetime(self) -> datetime:
        """Read a date-time (with seconds resolution) stored in 7 bytes

        :returns: Datetime
        :raises EOFError: If there are fewer than 7 bytes left in the source
        """
        year = self.read_sint(2)
        month = self.read_uint(1)
        day = self.read_uint(1)
        hour = self.read_uint(1)
        minute = self.read_uint(1)
        second = self.read_uint(1)
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

    def read_timestamp_v7(self) -> Timestamp:
        """Read a version 7 mediatimestamp.Timestamp with no sign

        :returns: Timestamp
        :raises EOFError: If there are fewer than 10 bytes left in the source
        """
        secs = self.read_uint(6)
        nano = self.read_uint(4)
        return Timestamp(secs, nano)

    def read_timestamp(self) -> Timestamp:
        """Read a mediatimestamp.Timestamp

        :returns: Timestamp
        :raises EOFError: If there are fewer than 11 bytes left in the source
        """
        if self.read_bool():
            sign = 1
        else:
            sign = -1
        secs = self.read_uint(6)
        nano = self.read_uint(4)
        return Timestamp(secs, nano, sign)

    def read_rational(self) -> Fraction:
        """Read a rational (fraction)

        If numerator or denominator is 0, returns Fraction(0)

        :returns: fraction.Fraction
        :raises EOFError: If there are fewer than 8 bytes left in the source
        """
        numerator = self.read_uint(4)
        denominator = self.read_uint(4)
        if numerator == 0 or denominator == 0:
            return Fraction(0)
        else:
            return Fraction(numerator, denominator)

    def read_varbytes(self) -> bytes:
        """Read a variable length byte array

        Reads a 4 byte uint to get the byte array length, then reads bytes of that length

        :returns: bytes
        :raises EOFError: If there are too few bytes left in the source
        """
        length = self.read_uint(4)
        return self.file_data.read(length)

    def skip(self, length: int) -> None:
        """Skip length bytes

        :param length: Number of bytes to skip
        """
        self.file_data.seek(length, SEEK_CUR)


class GrainDataLoadingMode (Enum):
    """This enumeration describes the mode for loading grains from the input.

    For a Non-seekable input:
        LOAD_IMMEDIATELY -- Grain data will be read as the stream is processed
        ALWAYS_LOAD_DEFER_IF_POSSIBLE -- Grain data will be read as the stream is processed
        ALWAYS_DEFER_LOAD_IF_POSSIBLE -- Grain data will be read as the stream is processed
        LOAD_NEVER -- Grain data will be skipped over

    For a Seekable input:
        LOAD_IMMEDIATELY -- Grain data will be read as the stream is processed
        ALWAYS_LOAD_DEFER_IF_POSSIBLE -- Grain data will be skipped initially, but loaded
                                         upon request. All unloaded grains will be loaded when
                                         the context manager is exited.
        ALWAYS_DEFER_LOAD_IF_POSSIBLE -- Grain data will be skipped initially, but loaded
                                         upon request. All unloaded grains will have their data
                                         loading canceled when the context manager is exited.
        LOAD_NEVER -- Grain data will be skipped over
    """
    LOAD_IMMEDIATELY = 0
    ALWAYS_LOAD_DEFER_IF_POSSIBLE = 1
    ALWAYS_DEFER_LOAD_IF_POSSIBLE = 2
    LOAD_NEVER = 3


class BaseGSFDecoderSession(object):
    """Base class that provides methods for parsing header metadata from a buffered SyncGSFBlock"""
    def __init__(self):
        self.major = 0
        self.minor = 0

    def _sync_decode_head(self,
                          head_block: SyncGSFBlock) -> GSFFileHeaderDict:
        """Decode the "head" block and extract ID, created date, segments and tags

        :param head_block: SyncGSFBlock representing the "head" block
        :returns: Head block as a dict
        """
        head: GSFFileHeaderDict = {}
        head['id'] = head_block.read_uuid()
        head['created'] = head_block.read_datetime()

        head['segments'] = []
        head['tags'] = []

        # Read head block children
        for head_child in head_block.child_blocks():
            # Parse a segment block
            if head_child.tag == "segm":
                segm = {}
                segm['local_id'] = head_child.read_uint(2)
                segm['id'] = head_child.read_uuid()
                segm['count'] = head_child.read_sint(8)
                segm['tags'] = []

                # Segment blocks can have child tags as well
                while head_child.has_child_block():
                    with SyncGSFBlock(head_block) as segm_child:
                        if segm_child.tag == "flow":
                            src_id = segm_child.read_uuid()
                            flow_id = segm_child.read_uuid()
                            format = segm_child.read_string(64)
                            data = segm_child.read_varbytes()
                            segm['flow'] = {
                                'source_id': src_id,
                                'flow_id': flow_id,
                                'format': format,
                                'data': data.decode('utf-8')
                            }
                        elif segm_child.tag == "tag ":
                            key = segm_child.read_varstring()
                            value = segm_child.read_varstring()
                            segm['tags'].append((key, value))

                head['segments'].append(segm)

            # Parse a tag block
            elif head_child.tag == "tag ":
                key = head_child.read_varstring()
                value = head_child.read_varstring()
                head['tags'].append((key, value))

        return cast(GSFFileHeaderDict, head)

    def _sync_decode_tils(self, tils_block: SyncGSFBlock) -> List[dict]:
        """Decode timelabels (tils) block

        :param tils_block: Instance of SyncGSFBlock() representing a "gbhd" block
        :returns: tils block as a dict
        """
        tils = []
        timelabel_count = tils_block.read_uint(2)
        for i in range(0, timelabel_count):
            tag = tils_block.read_string(16)
            tag = tag.strip("\x00")
            count = tils_block.read_uint(4)
            rate = tils_block.read_rational()
            drop = tils_block.read_bool()

            tils.append({'tag': tag,
                         'timelabel': {'frames_since_midnight': count,
                                       'frame_rate_numerator': rate.numerator,
                                       'frame_rate_denominator': rate.denominator,
                                       'drop_frame': drop}})

        return tils

    def _sync_decode_gbhd(self, gbhd_block: SyncGSFBlock) -> GrainMetadataDict:
        """Decode grain block header ("gbhd") to get grain metadata

        :param gbhd_block: Instance of GSFBlock() representing a "gbhd" block
        :returns: Grain data dict
        :raises GSFDecodeError: If "gbhd" block contains an unkown child block
        """
        meta: dict = {
            "grain": {
            }
        }

        meta['grain']['source_id'] = gbhd_block.read_uuid()
        meta['grain']['flow_id'] = gbhd_block.read_uuid()
        if self.major == 7:
            gbhd_block.skip(16)  # Skip over deprecated byte array
            meta['grain']['origin_timestamp'] = gbhd_block.read_timestamp_v7()
            meta['grain']['sync_timestamp'] = gbhd_block.read_timestamp_v7()
        else:
            meta['grain']['origin_timestamp'] = gbhd_block.read_timestamp()
            meta['grain']['sync_timestamp'] = gbhd_block.read_timestamp()
        meta['grain']['rate'] = gbhd_block.read_rational()
        meta['grain']['duration'] = gbhd_block.read_rational()

        for gbhd_child in gbhd_block.child_blocks():
            if gbhd_child.tag == "tils":
                meta['grain']['timelabels'] = self._sync_decode_tils(gbhd_child)
            elif gbhd_child.tag == "vghd":
                meta['grain']['grain_type'] = 'video'
                meta['grain']['cog_frame'] = {}
                meta['grain']['cog_frame']['format'] = gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['layout'] = gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['width'] = gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['height'] = gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['extension'] = gbhd_child.read_uint(4)

                src_aspect_ratio = gbhd_child.read_rational()
                if src_aspect_ratio != 0:
                    meta['grain']['cog_frame']['source_aspect_ratio'] = {
                        'numerator': src_aspect_ratio.numerator,
                        'denominator': src_aspect_ratio.denominator
                    }

                pixel_aspect_ratio = gbhd_child.read_rational()
                if pixel_aspect_ratio != 0:
                    meta['grain']['cog_frame']['pixel_aspect_ratio'] = {
                        'numerator': pixel_aspect_ratio.numerator,
                        'denominator': pixel_aspect_ratio.denominator
                    }

                meta['grain']['cog_frame']['components'] = []
                for comp_block in gbhd_child.child_blocks():
                    if comp_block.tag != 'comp':
                        continue

                    # Guard against bad files with multiple 'comp'
                    meta['grain']['cog_frame']['components'] = []

                    comp_count = comp_block.read_uint(2)
                    offset = 0
                    for i in range(0, comp_count):
                        comp = {}
                        comp['width'] = comp_block.read_uint(4)
                        comp['height'] = comp_block.read_uint(4)
                        comp['stride'] = comp_block.read_uint(4)
                        comp['length'] = comp_block.read_uint(4)
                        comp['offset'] = offset
                        offset += comp['length']
                        meta['grain']['cog_frame']['components'].append(comp)

            elif gbhd_child.tag == 'cghd':
                meta['grain']['grain_type'] = "coded_video"
                meta['grain']['cog_coded_frame'] = {}
                meta['grain']['cog_coded_frame']['format'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['layout'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['origin_width'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['origin_height'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['coded_width'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['coded_height'] = gbhd_child.read_uint(4)
                if self.major < 9:
                    meta['grain']['cog_coded_frame']['is_key_frame'] = gbhd_child.read_bool()
                    meta['grain']['cog_coded_frame']['temporal_offset'] = gbhd_child.read_sint(4)
                else:
                    is_key_frame = gbhd_child.read_optional_bool()
                    if is_key_frame is not None:
                        meta['grain']['cog_coded_frame']['is_key_frame'] = is_key_frame
                    temporal_offset = gbhd_child.read_optional_sint(4, 0x7fffffff)
                    if temporal_offset is not None:
                        meta['grain']['cog_coded_frame']['temporal_offset'] = temporal_offset

                for unof_block in gbhd_child.child_blocks():
                    if unof_block.tag != 'unof':
                        continue

                    meta['grain']['cog_coded_frame']['unit_offsets'] = []

                    unit_offsets = unof_block.read_uint(2)
                    for i in range(0, unit_offsets):
                        meta['grain']['cog_coded_frame']['unit_offsets'].append(unof_block.read_uint(4))

            elif gbhd_child.tag == "aghd":
                meta['grain']['grain_type'] = "audio"
                meta['grain']['cog_audio'] = {}
                meta['grain']['cog_audio']['format'] = gbhd_child.read_uint(4)
                meta['grain']['cog_audio']['channels'] = gbhd_child.read_uint(2)
                meta['grain']['cog_audio']['samples'] = gbhd_child.read_uint(4)
                meta['grain']['cog_audio']['sample_rate'] = gbhd_child.read_uint(4)

            elif gbhd_child.tag == "cahd":
                meta['grain']['grain_type'] = "coded_audio"
                meta['grain']['cog_coded_audio'] = {}
                meta['grain']['cog_coded_audio']['format'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['channels'] = gbhd_child.read_uint(2)
                meta['grain']['cog_coded_audio']['samples'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['priming'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['remainder'] = gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['sample_rate'] = gbhd_child.read_uint(4)

            elif gbhd_child.tag == "eghd":
                meta['grain']['grain_type'] = "event"

        return cast(GrainMetadataDict, meta)


class GSFAsyncDecoderSession(BaseGSFDecoderSession):
    def __init__(self,
                 parse_grain: ParseGrainType,
                 file_data: OpenAsyncBinaryIO,
                 sync_compatibility_mode: bool,
                 support_concatenation: bool = True):
        super().__init__()
        self.file_data = file_data

        if not self.file_data.seekable_forwards():
            raise RuntimeError("Cannot decode a stream that is not at least forward seekable")

        self.Grain = parse_grain
        self.file_headers: Optional[GSFFileHeaderDict] = None

        self._exiting = False
        self._unloaded_lazy_grains: Dict[int, Grain] = {}
        self._next_lazy_grain_number = 0

        self._sync_compatibility_mode = sync_compatibility_mode
        self._support_concatenation = support_concatenation

    async def _decode_ssb_header(self, head_tag=""):
        """Find and read the SSB header in the GSF file

        :returns: (major, minor) version tuple
        :raises GSFDecodeBadFileTypeError: If the SSB tag shows this isn't a GSF file
        """
        ssb_block = AsyncGSFBlock(self.file_data)

        if not head_tag:
            head_tag = await ssb_block.read_string(8)

        if head_tag != "SSBBgrsg":
            raise GSFDecodeBadFileTypeError("File lacks correct header", ssb_block.block_start, head_tag)

        major = await ssb_block.read_uint(2)
        minor = await ssb_block.read_uint(2)

        return (major, minor)

    async def _decode_file_headers(self, head_tag="") -> None:
        """Verify the file is a supported version, get the file header and store it in the file_headers property

        :raises GSFDecodeBadVersionError: If the file version is not supported
        :raises GSFDecodeBadFileTypeError: If this isn't a GSF file
        :raises GSFDecodeError: If the file doesn't have a "head" block
        """
        (self.major, self.minor) = await self._decode_ssb_header(head_tag=head_tag)
        if self.major not in [7, 8, 9]:
            raise GSFDecodeBadVersionError(f"Unknown Version {self.major}.{self.minor}", 0, self.major, self.minor)

        try:
            async with AsyncGSFBlock(self.file_data, want_tag="head") as head_block:
                self.file_headers = self._sync_decode_head(await head_block.read_remaining_block())
        except EOFError:
            raise GSFDecodeError("No head block found in file", self.file_data.tell())

    def _add_lazy_grain(self, key: int, grain: Grain):
        self._unloaded_lazy_grains[key] = grain

    def _remove_lazy_grain(self, key: int):
        del self._unloaded_lazy_grains[key]

    async def _kill_unused_lazy_loaders(self):
        self._exiting = True
        for (key, grain) in self._unloaded_lazy_grains.items():
            await grain

    async def _load_unused_lazy_loaders(self):
        for (key, grain) in list(self._unloaded_lazy_grains.items()):
            await grain

    async def grains(self,
                     local_ids: Optional[Sequence[int]] = None,
                     loading_mode: GrainDataLoadingMode = GrainDataLoadingMode.ALWAYS_DEFER_LOAD_IF_POSSIBLE
                     ) -> AsyncIterable[Tuple[Grain, int]]:
        """Generator to get grains from the GSF file. Skips blocks which aren't "grai".

        The file_data will be positioned after the `grai` block.

        :param local_ids: A list of local-ids to include in the output. If None (the default) then all local-ids will
                          be included
        :param loading_mode: The mode to use when loading grain data elements. For modes ALWAYS_DEFER_LOAD_IF_POSSIBLE
                             and ALWAYS_LOAD_DEFER_IF_POSSIBLE with a seekable input the grain data can be loaded later
                             by awaiting the grain object itself. as long as you are still inside this context manager.
                             When the context manager exits all grains are either implicitly loaded or rendered
                             permanently empty.
        :yields: (Grain, local_id) tuple for each grain
        :raises GSFDecodeError: If grain is invalid (e.g. no "gbhd" child)
        """
        async def _read_out_of_order(parent: GSFAsyncDecoderSession,
                                     key: int,
                                     file_data: OpenAsyncBinaryIO,
                                     pos: int,
                                     length: int,
                                     load_on_exit=False) -> Optional[bytes]:
            if load_on_exit or not parent._exiting:
                parent._remove_lazy_grain(key)

                oldpos = file_data.tell()
                file_data.seek(pos)
                data = await file_data.read(length)
                file_data.seek(oldpos)
                return data
            else:
                return None

        have_concatenation = False

        while True:
            try:
                if have_concatenation:
                    await self._decode_file_headers(head_tag="SSBBgrsg")
                    have_concatenation = False

                async with AsyncGSFBlock(self.file_data) as block:
                    if block.tag != "grai":
                        if block.tag == "SSBB":
                            if not self._support_concatenation:
                                break
                            have_concatenation = True
                        continue

                    grai_block = block
                    if grai_block.size == 0:
                        # Terminator block reached
                        if self._support_concatenation:
                            continue
                        break

                    local_id = await grai_block.read_uint(2)

                    if local_ids is not None and local_id not in local_ids:
                        continue

                    async with AsyncGSFBlock(grai_block, want_tag="gbhd", raise_on_wrong_tag=True) as gbhd_block:
                        meta = self._sync_decode_gbhd(await gbhd_block.read_remaining_block())

                    data: Optional[Union[bytes, Awaitable[Optional[bytes]]]] = None

                    data_length = 0
                    if grai_block.has_child_block():
                        async with AsyncGSFBlock(grai_block, want_tag="grdt") as grdt_block:
                            if grdt_block.get_remaining() > 0:
                                if self.file_data.seekable_backwards() and loading_mode in [
                                 GrainDataLoadingMode.ALWAYS_DEFER_LOAD_IF_POSSIBLE,
                                 GrainDataLoadingMode.ALWAYS_LOAD_DEFER_IF_POSSIBLE]:
                                    if not self._sync_compatibility_mode:
                                        # It is correct that this is not awaited here
                                        # It will be awaited when the data is actually needed.
                                        load_on_exit = (
                                            loading_mode == GrainDataLoadingMode.ALWAYS_LOAD_DEFER_IF_POSSIBLE)
                                        data = _read_out_of_order(self,
                                                                  self._next_lazy_grain_number,
                                                                  self.file_data,
                                                                  self.file_data.tell(),
                                                                  grdt_block.get_remaining(),
                                                                  load_on_exit=load_on_exit)
                                        data_length = grdt_block.get_remaining()
                                    else:
                                        # This is compatibility mode with the old code
                                        data = IOBytes(cast(OpenAsyncFileWrapper, self.file_data).getsync(),
                                                       self.file_data.tell(),
                                                       grdt_block.get_remaining())
                                elif loading_mode == GrainDataLoadingMode.LOAD_NEVER:
                                    if self.file_data.seekable_forwards():
                                        self.file_data.seek(grdt_block.get_remaining(), SEEK_CUR)
                                    else:
                                        await self.file_data.read(grdt_block.get_remaining())
                                else:
                                    data = await self.file_data.read(grdt_block.get_remaining())

                grain = self.Grain(meta, data)

                if isawaitable(data):
                    grain.length = data_length
                    self._add_lazy_grain(self._next_lazy_grain_number, grain)
                    self._next_lazy_grain_number += 1

                yield (grain, local_id)
            except EOFError:
                return  # We ran out of grains to read and hit EOF


class GSFSyncDecoderSession(BaseGSFDecoderSession):
    def __init__(self,
                 parse_grain: ParseGrainType,
                 file_data: IO[bytes],
                 support_concatenation: bool = True):
        super().__init__()
        self.file_data = file_data

        self.Grain = parse_grain
        self.file_headers: Optional[GSFFileHeaderDict] = None

        self._support_concatenation = support_concatenation

        self._exiting = False

    def _decode_ssb_header(self, head_tag=""):
        """Find and read the SSB header in the GSF file

        :returns: (major, minor) version tuple
        :raises GSFDecodeBadFileTypeError: If the SSB tag shows this isn't a GSF file
        """
        ssb_block = SyncGSFBlock(self.file_data)

        if not head_tag:
            head_tag = ssb_block.read_string(8)

        if head_tag != "SSBBgrsg":
            raise GSFDecodeBadFileTypeError("File lacks correct header", ssb_block.block_start, head_tag)

        major = ssb_block.read_uint(2)
        minor = ssb_block.read_uint(2)

        return (major, minor)

    def _decode_file_headers(self, head_tag="") -> None:
        """Verify the file is a supported version, get the file header and store it in the file_headers property

        :raises GSFDecodeBadVersionError: If the file version is not supported
        :raises GSFDecodeBadFileTypeError: If this isn't a GSF file
        :raises GSFDecodeError: If the file doesn't have a "head" block
        """
        (self.major, self.minor) = self._decode_ssb_header(head_tag=head_tag)
        if self.major not in [7, 8, 9]:
            raise GSFDecodeBadVersionError(f"Unknown Version {self.major}.{self.minor}", 0, self.major, self.minor)

        try:
            with SyncGSFBlock(self.file_data, want_tag="head") as head_block:
                self.file_headers = self._sync_decode_head(head_block.read_remaining_block())
        except EOFError:
            raise GSFDecodeError("No head block found in file", self.file_data.tell())

    def grains(self,
               local_ids: Optional[Sequence[int]] = None,
               loading_mode: GrainDataLoadingMode = GrainDataLoadingMode.ALWAYS_DEFER_LOAD_IF_POSSIBLE
               ) -> Iterable[Tuple[Grain, int]]:
        """Generator to get grains from the GSF file. Skips blocks which aren't "grai".

        The file_data will be positioned after the `grai` block.

        :param local_ids: A list of local-ids to include in the output. If None (the default) then all local-ids will
                          be included
        :param loading_mode: The mode to use when loading grain data elements. For modes ALWAYS_DEFER_LOAD_IF_POSSIBLE
                             and ALWAYS_LOAD_DEFER_IF_POSSIBLE with a seekable input the grain data can be loaded later
                             by awaiting the grain object itself. as long as you are still inside this context manager.
                             When the context manager exits all grains are either implicitly loaded or rendered
                             permanently empty.
        :yields: (Grain, local_id) tuple for each grain
        :raises GSFDecodeError: If grain is invalid (e.g. no "gbhd" child)
        """
        have_concatenation = False

        while True:
            try:
                if have_concatenation:
                    self._decode_file_headers(head_tag="SSBBgrsg")
                    have_concatenation = False

                with SyncGSFBlock(self.file_data) as block:
                    if block.tag != "grai":
                        if block.tag == "SSBB":
                            if not self._support_concatenation:
                                break
                            have_concatenation = True
                        continue

                    grai_block = block
                    if grai_block.size == 0:
                        # Terminator block reached
                        if self._support_concatenation:
                            continue
                        break

                    local_id = grai_block.read_uint(2)

                    if local_ids is not None and local_id not in local_ids:
                        continue

                    with SyncGSFBlock(grai_block, want_tag="gbhd", raise_on_wrong_tag=True) as gbhd_block:
                        meta = self._sync_decode_gbhd(gbhd_block.read_remaining_block())

                    data: Optional[Union[bytes, Awaitable[Optional[bytes]]]] = None

                    if grai_block.has_child_block():
                        with SyncGSFBlock(grai_block, want_tag="grdt") as grdt_block:
                            if grdt_block.get_remaining() > 0:
                                if self.file_data.seekable() and loading_mode in [
                                 GrainDataLoadingMode.ALWAYS_DEFER_LOAD_IF_POSSIBLE,
                                 GrainDataLoadingMode.ALWAYS_LOAD_DEFER_IF_POSSIBLE]:
                                    data = IOBytes(self.file_data,
                                                   self.file_data.tell(),
                                                   grdt_block.get_remaining())
                                elif loading_mode == GrainDataLoadingMode.LOAD_NEVER:
                                    if self.file_data.seekable():
                                        self.file_data.seek(grdt_block.get_remaining(), SEEK_CUR)
                                    else:
                                        self.file_data.read(grdt_block.get_remaining())
                                else:
                                    data = self.file_data.read(grdt_block.get_remaining())

                grain = self.Grain(meta, data)

                yield (grain, local_id)
            except EOFError:
                return  # We ran out of grains to read and hit EOF


class GSFDecoder(object):
    """A decoder for GSF format.

    The preferred interface for usage is to use this class as a context manager, which provides an instance of
    GSFDecoderSession.

    For backwards compatibility provides methods to decode the header of a GSF file, followed by a generator to
    get each grain, wrapped in some grain method (mediagrains.Grain by default.) These methods are deprecated
    and should not be used in new code.

    Can also be used to make a one-off decode of a GSF file from a bytes-like object by calling `decode(bytes_like)`.
    """
    def __init__(self,
                 parse_grain: ParseGrainType = GrainFactory,
                 file_data: Optional[Union[IO[bytes], AsyncBinaryIO, OpenAsyncBinaryIO]] = None,
                 **kwargs):
        """Constructor

        :param parse_grain: Function that takes a (metadata dict, buffer) and returns a grain representation
        :param file_data: BufferedReader (or similar) containing GSF data to decode
        """
        self._file_data: Optional[Union[RawIOBase, BufferedIOBase]]
        self._afile_data: Optional[AsyncBinaryIO]
        self._open_afile: Optional[OpenAsyncBinaryIO]

        self.Grain = parse_grain

        if isinstance(file_data, AsyncBinaryIO):
            self._afile_data = file_data
            self._open_afile = None
            self._file_data = None
        elif isinstance(file_data, OpenAsyncBinaryIO):
            self._afile_data = None
            self._open_afile = file_data
            self._file_data = None
        elif isinstance(file_data, BytesIO):
            self._afile_data = None
            self._open_afile = None
            self._file_data = cast(BufferedIOBase, file_data)
        elif isinstance(file_data, (RawIOBase, BufferedIOBase)):
            self._afile_data = None
            self._open_afile = None
            self._file_data = file_data
        else:
            self._afile_data = None
            self._open_afile = None
            self._file_data = None

        self._open_session: Optional[GSFSyncDecoderSession] = None
        self._open_asession: Optional[GSFAsyncDecoderSession] = None

        self._sync_compatibility_mode: bool = False
        self._support_concatenation = kwargs.get("support_concatenation", True)

    def __enter__(self) -> GSFSyncDecoderSession:
        if self._file_data is None:
            raise TypeError("file_data must be a synchronous binary file to use this class as a sync context manager")

        self._open_session = GSFSyncDecoderSession(file_data=cast(IO[bytes], self._file_data),
                                                   parse_grain=self.Grain,
                                                   support_concatenation=self._support_concatenation)
        self._open_session._decode_file_headers()
        return self._open_session

    def __exit__(self, *args, **kwargs):
        if self._open_session is not None:
            self._open_session = None

    async def __aenter__(self) -> GSFAsyncDecoderSession:
        if self._open_afile is None:
            if isinstance(self._afile_data, AsyncBinaryIO):
                self._open_afile = await self._afile_data.__aenter__()
            else:
                raise TypeError(
                    "file_data must be an asynchronous binary file to use this class as an async context manager")

        self._open_asession = GSFAsyncDecoderSession(file_data=self._open_afile,
                                                     parse_grain=self.Grain,
                                                     sync_compatibility_mode=self._sync_compatibility_mode,
                                                     support_concatenation=self._support_concatenation)
        await self._open_asession._decode_file_headers()
        return self._open_asession

    async def __aexit__(self, *args, **kwargs):
        if self._open_asession is not None:
            await self._open_asession._kill_unused_lazy_loaders()
            self._open_asession = None

        if self._open_afile is not None and self._afile_data is not None:
            await self._afile_data.__aexit__(*args, **kwargs)
            self._open_afile = None

    @deprecated(version="2.7.0", reason="This method is old, use the class as a context manager instead")
    def decode_file_headers(self) -> GSFFileHeaderDict:
        """Verify the file is a supported version, and get the file header

        :returns: File header data (segments and tags) as a dict
        :raises GSFDecodeBadVersionError: If the file version is not supported
        :raises GSFDecodeBadFileTypeError: If this isn't a GSF file
        :raises GSFDecodeError: If the file doesn't have a "head" block
        """
        self._open_session = self.__enter__()
        if self._open_session.file_headers is None:
            raise RuntimeError("There should be some file headers here!")
        return self._open_session.file_headers

    @deprecated(version="2.7.0", reason="This method is old, use the class as a context manager instead")
    def grains(self,
               local_ids: Optional[Sequence[int]] = None,
               skip_data: bool = False,
               load_lazily: bool = False):
        """Generator to get grains from the GSF file. Skips blocks which aren't "grai".

        The file_data will be positioned after the `grai` block.

        :param local_ids: A list of local-ids to include in the output. If None (the default) then all local-ids will be
                          included
        :param skip_data: If True, grain data blocks will be seeked over and only grain headers will be read
        :param load_lazily: If True, the grains returned will be designed to lazily load data from the underlying stream
                            only when it is needed. In this case the "skip_data" parameter will be ignored.
        :yields: (Grain, local_id) tuple for each grain
        :raises GSFDecodeError: If grain is invalid (e.g. no "gbhd" child)
        """
        if self._open_session is None:
            raise RuntimeError("Cannot access grains when no headers have been decoded")

        if load_lazily:
            mode = GrainDataLoadingMode.ALWAYS_LOAD_DEFER_IF_POSSIBLE
        elif skip_data:
            mode = GrainDataLoadingMode.LOAD_NEVER
        else:
            mode = GrainDataLoadingMode.LOAD_IMMEDIATELY

        return self._open_session.grains(local_ids=local_ids, loading_mode=mode)

    async def _asynchronously_decode(self) -> Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]:
        async with self as dec:
            grains: Dict[int, List[Grain]] = {}
            async for (grain, key) in dec.grains(loading_mode=GrainDataLoadingMode.LOAD_IMMEDIATELY):
                if key not in grains:
                    grains[key] = []
                grains[key].append(grain)
            if dec.file_headers is None:
                raise RuntimeError("There ought to be file headers here")
            return (dec.file_headers, grains)

    def _synchronously_decode(self) -> Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]:
        with self as dec:
            grains: Dict[int, List[Grain]] = {}
            for (grain, key) in dec.grains(loading_mode=GrainDataLoadingMode.LOAD_IMMEDIATELY):
                if key not in grains:
                    grains[key] = []
                grains[key].append(grain)
            if dec.file_headers is None:
                raise RuntimeError("There ought to be file headers here")
            return (dec.file_headers, grains)

    def decode(self, s: Optional[bytes] = None) -> Tuple[GSFFileHeaderDict, Dict[int, List[Grain]]]:
        """Decode a GSF formatted bytes object

        :param s: GSF-formatted bytes object, optional if `file_data` supplied to constructor
        :returns: A dictionary mapping sequence ids to lists of Grain objects (or subclasses of such).
        """
        if (s is not None):
            # Unclear why this cast is needed, since a BytesIO is already a BufferedIOBase ...
            self._file_data = cast(BufferedIOBase, BytesIO(s))

        return self._synchronously_decode()


class GSFEncodeError(GSFError):
    """A generic GSF Encoder error, all other GSF Encoder exceptions inherit from it."""
    pass


class GSFEncodeAddToActiveDump(GSFEncodeError):
    """An exception raised when trying to add something to the header of a GSF
    file which has already written its header to the stream."""
    pass


def _encode_uint(val: int, size: int) -> bytes:
    d = bytearray(size)
    for i in range(0, size):
        d[i] = (val & 0xFF)
        val >>= 8
    return bytes(d)


def _encode_sint(val: int, size: int) -> bytes:
    if val < 0:
        val = val + (1 << (8*size))
    return _encode_uint(val, size)


def _encode_bool(val: bool) -> bytes:
    return _encode_uint(1 if val else 0, 1)


def _encode_uuid(val: UUID) -> bytes:
    return val.bytes


def _encode_ts_v7(ts: Timestamp) -> bytes:
    return (_encode_uint(ts.sec, 6) +
            _encode_uint(ts.ns, 4))


def _encode_ts(ts: Timestamp) -> bytes:
    return (_encode_bool(ts.sign >= 0) +
            _encode_uint(ts.sec, 6) +
            _encode_uint(ts.ns, 4))


def _encode_rational(value: RationalTypes) -> bytes:
    value = Fraction(value)
    return (_encode_uint(value.numerator, 4) +
            _encode_uint(value.denominator, 4))


def _ensure_utc_datetime(value: datetime) -> datetime:
    utc_value = datetime(
        value.year,
        value.month,
        value.day,
        value.hour,
        value.minute,
        value.second,
        value.microsecond,
        tzinfo=timezone.utc
    )

    # If the value is timezone aware then subtract the UTC offset to get the actual UTC value
    # else the timezone is assumed to be UTC
    if value.tzinfo is not None:
        utc_offset = value.tzinfo.utcoffset(value)
        if utc_offset is not None:
            utc_value = utc_value - utc_offset

    return utc_value


class OpenGSFEncoderBase(object):
    def __init__(self,
                 major: int,
                 minor: int,
                 id: UUID,
                 created: datetime,
                 tags: List["GSFEncoderTag"],
                 segments: Dict[int, "GSFEncoderSegment"],
                 streaming: bool,
                 next_local: int):
        self.major = major
        self.minor = minor
        self._tags = tags
        self.streaming = streaming
        self.id = id
        self.created = _ensure_utc_datetime(created)
        self._segments = segments
        self._next_local = next_local
        self._active_dump = False

    @property
    def tags(self) -> Tuple["GSFEncoderTag", ...]:
        return tuple(self._tags)

    @property
    def segments(self) -> Mapping[int, "GSFEncoderSegment"]:
        return frozendict(self._segments)

    def add_tag(self, key: str, value: str):
        """Add a tag to the file"""
        if self._active_dump:
            raise GSFEncodeAddToActiveDump("Cannot add a new tag to an encoder that is currently dumping")

        self._tags.append(GSFEncoderTag(key, value))

    def add_segment(self, id: Optional[UUID] = None, local_id: Optional[int] = None,
                    tags: Optional[Iterable[Tuple[str, str]]] = None) -> "GSFEncoderSegment":
        """Add a segment to the file, if id is specified it should be a uuid,
        otherwise one will be generated. If local_id is specified it should be an
        integer, otherwise the next available integer will be used. Returns the newly
        created segment."""

        if local_id is None:
            local_id = self._next_local
        if local_id >= self._next_local:
            self._next_local = local_id + 1
        if local_id in self._segments:
            raise GSFEncodeError("Segment local id {} already in use".format(local_id))

        if id is None:
            id = uuid1()

        if self._active_dump:
            raise GSFEncodeAddToActiveDump(
                "Cannot add a new segment {} ({!s}) to an encoder that is currently dumping".format(local_id, id))

        seg = GSFEncoderSegment(id, local_id, tags=tags, parent=self)
        self._segments[local_id] = seg
        return seg

    def _get_segment(self, segment_id: Optional[UUID], segment_local_id: Optional[int]) -> "GSFEncoderSegment":
        if segment_local_id is None:
            segments = sorted([local_id for local_id in self._segments if
                               segment_id is None or self._segments[local_id].id == segment_id])
            if len(segments) > 0:
                segment_local_id = segments[0]
        if segment_local_id is not None and segment_local_id in self._segments:
            segment = self._segments[segment_local_id]
        else:
            if self._active_dump:
                raise GSFEncodeError("Cannot add a segment to a progressive dump")
            segment = self.add_segment(id=segment_id, local_id=segment_local_id)

        return segment

    def _set_segment_offsets(self, segment_offsets: Iterable[Tuple["GSFEncoderSegment", int]], pos: int) -> None:
        for (seg, offset) in segment_offsets:
            seg.set_size_position(pos + offset)

    def _encode_file_header(self):
        return (b"SSBB" +
                b"grsg" +
                _encode_uint(self.major, 2) +
                _encode_uint(self.minor, 2))

    def _encode_head_block(self, all_at_once: bool = False) -> Tuple[bytes, List[Tuple["GSFEncoderSegment", int]]]:
        size = (31 +
                sum(seg.segm_block_size for seg in self._segments.values()) +
                sum(tag.tag_block_size for tag in self._tags))

        data = (
            b"head" +
            _encode_uint(size, 4) +
            _encode_uuid(self.id) +
            _encode_sint(self.created.year, 2) +
            _encode_uint(self.created.month, 1) +
            _encode_uint(self.created.day, 1) +
            _encode_uint(self.created.hour, 1) +
            _encode_uint(self.created.minute, 1) +
            _encode_uint(self.created.second, 1))
        offsets = []

        for seg in self._segments.values():
            (seg_data, offset) = seg._encode_header(all_at_once=all_at_once)
            offsets.append((seg, len(data) + offset))
            data += seg_data

        for tag in self._tags:
            data += bytes(tag)

        return (data, offsets)

    def _encode_all_grains(self):
        data = b''
        for seg in self._segments.values():
            data += seg.encode_all_grains()
        return data


class OpenGSFEncoder(OpenGSFEncoderBase):
    def __init__(self,
                 file: IO[bytes],
                 major: int,
                 minor: int,
                 id: UUID,
                 created: datetime,
                 tags: List["GSFEncoderTag"],
                 segments: Dict[int, "GSFEncoderSegment"],
                 streaming: bool,
                 next_local: int):
        super().__init__(major, minor, id, created, tags, segments, streaming, next_local)
        self.file = file

    def add_grain(self,
                  grain: Grain,
                  segment_id: Optional[UUID] = None,
                  segment_local_id: Optional[int] = None):
        """Add a grain to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        self.add_grains((grain,), segment_id=segment_id, segment_local_id=segment_local_id)

    def add_grains(self,
                   grains: Iterable[Grain],
                   segment_id: Optional[UUID] = None,
                   segment_local_id: Optional[int] = None):
        """Add several grains to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        segment = self._get_segment(segment_id, segment_local_id)

        if self._active_dump:
            for grain in grains:
                self.file.write(segment.encode_grain(grain))
        else:
            segment.add_grains(grains)

    def _truncate(self):
        if self.file.seekable():
            self.file.seek(0)
            self.file.truncate()

    def _start_dump(self, all_at_once: bool = False):
        self._active_dump = True

        self._truncate()

        file_header = self._encode_file_header()

        (head_block, segment_offsets) = self._encode_head_block(all_at_once=all_at_once)
        if not all_at_once and self.file.seekable():
            self._set_segment_offsets(segment_offsets, self.file.tell() + len(file_header))

        self.file.write(file_header +
                        head_block +
                        self._encode_all_grains())

    def _end_dump(self):
        for seg in self._segments.values():
            if self.file.seekable() and seg._count_pos != -1:
                curpos = self.file.tell()
                self.file.seek(seg._count_pos)
                self.file.write(_encode_sint(seg.get_write_count(), 8))
                self.file.seek(curpos)

        if self._active_dump:
            self.file.write(b"grai" +
                            _encode_uint(0, 4))
            self._active_dump = False


class OpenAsyncGSFEncoder(OpenGSFEncoderBase):
    def __init__(self,
                 file: Union[AsyncBinaryIO, OpenAsyncBinaryIO],
                 major: int,
                 minor: int,
                 id: UUID,
                 created: datetime,
                 tags: List["GSFEncoderTag"],
                 segments: Dict[int, "GSFEncoderSegment"],
                 streaming: bool,
                 next_local: int):
        super().__init__(major, minor, id, created, tags, segments, streaming, next_local)
        self.file: Optional[AsyncBinaryIO]
        self._open_file: Optional[OpenAsyncBinaryIO]

        if isinstance(file, AsyncBinaryIO):
            self.file = file
            self._open_file = None
        else:
            self.file = None
            self._open_file = file

    async def add_grain(self,
                        grain: Grain,
                        segment_id: Optional[UUID] = None,
                        segment_local_id: Optional[int] = None):
        """Add a grain to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        await self.add_grains((grain,), segment_id=segment_id, segment_local_id=segment_local_id)

    async def add_grains(self,
                         grains: Iterable[Grain],
                         segment_id: Optional[UUID] = None,
                         segment_local_id: Optional[int] = None):
        """Add several grains to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        segment = self._get_segment(segment_id, segment_local_id)

        if self._open_file is not None and self._active_dump:
            for grain in grains:
                await self._open_file.write(segment.encode_grain(grain))
        else:
            segment.add_grains(grains)

    async def _truncate(self) -> None:
        if self._open_file is not None and self._open_file.seekable():
            self._open_file.seek(0)
            await self._open_file.truncate()

    async def _start_dump(self, all_at_once: bool = False):
        self._active_dump = True

        if self._open_file is None:
            if self.file is not None:
                self._open_file = await self.file.__aenter__()
            else:
                raise GSFEncodeError("Tried to encode to a file without a file")

        await self._truncate()

        file_header = self._encode_file_header()

        (head_block, segment_offsets) = self._encode_head_block(all_at_once=all_at_once)

        if not all_at_once and self._open_file.seekable():
            self._set_segment_offsets(segment_offsets, self._open_file.tell() + len(file_header))

        await self._open_file.write(file_header +
                                    head_block +
                                    self._encode_all_grains())

    async def _end_dump(self):
        for seg in self._segments.values():
            if self._open_file.seekable() and seg._count_pos != -1:
                curpos = self._open_file.tell()
                self._open_file.seek(seg._count_pos)

                await self._open_file.write(_encode_sint(seg.get_write_count(), 8))

                self._open_file.seek(curpos)

        if self._active_dump:
            await self._open_file.write(b"grai" +
                                        _encode_uint(0, 4))

            self._active_dump = False


class SegmentDict(TypedDict, total=False):
    id: UUID
    local_id: int
    tags: Iterable[Tuple[str, str]]


class GSFEncoder(object):
    """An encoder for GSF format.

    Constructor takes a single mandatory argument, an io.BytesIO-like object to which the result will be written,
    optional arguments exist for specifying file-level metadata, if no created time is specified the current time
    will be used, if no id is specified one will be generated randomly.


    The recommended interface is to use the encoder as either a context manager or an asynchronous context
    manager. Whilst in the context manager new grains can be added with add_grain, and upon leaving the context
    manager the grains will be written to the file. If the `streaming=True` parameter is passed to the constructor
    then calls to add_grain within the context manager will instead cause the grain to be written immediately.

    And older deprecated interface exists for synchronous work: the method add_grain and dump which add a grain to
    the file and dump the file the the buffer respectively.

    If a streaming format is required then you can instead use the "start_dump" method, followed by adding
    grains as needed, and then the "end_dump" method. Each new grain will be written as it is added. In this mode
    any segments in use MUST be added first before start_dump is called.

    In addition the following properties provide access to file-level metadata:

    major    -- an integer (default 8)
    minor    -- an integer (default 0)
    id       -- a uuid.UUID
    created  -- a datetime.datetime
    tags     -- a tuple of tags
    segments -- a frozendict of GSFEncoderSegments

    The current version of the library is designed for compatibility with v.9.0 of the GSF format."""
    def __init__(self,
                 file: Union[IO[bytes], AsyncBinaryIO, OpenAsyncBinaryIO],
                 major: int = 9,
                 minor: int = 0,
                 id: Optional[UUID] = None,
                 created: Optional[datetime] = None,
                 tags: Optional[Iterable[Tuple[str, str]]] = None,
                 segments: Iterable[SegmentDict] = [],
                 streaming: bool = False):
        self.file = file
        self.major = major
        self.minor = minor
        self._tags: List["GSFEncoderTag"] = []
        self.streaming = streaming
        self._open_encoder: Optional[OpenGSFEncoder] = None
        self._open_async_encoder: Optional[OpenAsyncGSFEncoder] = None
        self._next_local = 1

        if id is None:
            self.id = uuid1()
        else:
            self.id = id

        if created is None:
            self.created = datetime.now(timezone.utc)
        else:
            self.created = _ensure_utc_datetime(created)

        self._segments: Dict[int, "GSFEncoderSegment"] = {}

        if segments is not None:
            for seg in segments:
                try:
                    self.add_segment(**seg)
                except (TypeError, IndexError):
                    raise GSFEncodeError("No idea how to turn {!r} into a segment".format(seg))

        if tags is not None:
            for tag in tags:
                try:
                    self.add_tag(tag[0], tag[1])
                except (TypeError, IndexError):
                    raise GSFEncodeError("No idea how to turn {!r} into a tag".format(tag))

    def __enter__(self) -> OpenGSFEncoder:
        if not isinstance(self.file, RawIOBase) and not isinstance(self.file, BufferedIOBase):
            raise ValueError("To use in synchronous mode the file must be a synchronously writeable file")
        file = cast(IO[bytes], self.file)
        self._open_encoder = OpenGSFEncoder(file,
                                            self.major,
                                            self.minor,
                                            self.id,
                                            self.created,
                                            self._tags,
                                            self._segments,
                                            self.streaming,
                                            self._next_local)
        if self.streaming:
            self._open_encoder._start_dump(all_at_once=False)
        return self._open_encoder

    def __exit__(self, *args, **kwargs):
        if self._open_encoder is not None:
            if not self.streaming:
                self._open_encoder._start_dump(all_at_once=True)
            self._open_encoder._end_dump()
            self._next_local = self._open_encoder._next_local
            self._open_encoder = None

    async def __aenter__(self):
        if not isinstance(self.file, AsyncBinaryIO) and not isinstance(self.file, OpenAsyncBinaryIO):
            f = AsyncFileWrapper(self.file)
        else:
            f = self.file
        self._open_async_encoder = OpenAsyncGSFEncoder(f,
                                                       self.major,
                                                       self.minor,
                                                       self.id,
                                                       self.created,
                                                       self._tags,
                                                       self._segments,
                                                       self.streaming,
                                                       self._next_local)
        if self.streaming:
            await self._open_async_encoder._start_dump(all_at_once=False)
        return self._open_async_encoder

    async def __aexit__(self, *args, **kwargs):
        if self._open_async_encoder is not None:
            if not self.streaming:
                await self._open_async_encoder._start_dump(all_at_once=True)
            await self._open_async_encoder._end_dump()
            self._next_local = self._open_async_encoder._next_local
            self._open_async_encoder = None

    @property
    def tags(self) -> Tuple["GSFEncoderTag", ...]:
        return tuple(self._tags)

    @property
    def segments(self) -> Mapping[int, "GSFEncoderSegment"]:
        return frozendict(self._segments)

    def add_tag(self, key: str, value: str):
        """Add a tag to the file"""
        if self._open_encoder is not None:
            raise GSFEncodeAddToActiveDump("Cannot add a new tag to an encoder that is currently dumping")

        self._tags.append(GSFEncoderTag(key, value))

    def add_segment(self, id: Optional[UUID] = None, local_id: Optional[int] = None,
                    tags: Optional[Iterable[Tuple[str, str]]] = None) -> "GSFEncoderSegment":
        """Add a segment to the file, if id is specified it should be a uuid,
        otherwise one will be generated. If local_id is specified it should be an
        integer, otherwise the next available integer will be used. Returns the newly
        created segment."""

        if self._open_encoder is not None:
            raise GSFEncodeAddToActiveDump(
                "Cannot add a new segment {} ({!s}) to an encoder that is currently dumping".format(local_id, id))

        if local_id is None:
            local_id = self._next_local
        if local_id >= self._next_local:
            self._next_local = local_id + 1
        if local_id in self._segments:
            raise GSFEncodeError("Segment local id {} already in use".format(local_id))

        if id is None:
            id = uuid1()

        seg = GSFEncoderSegment(id, local_id, tags=tags, parent=self)
        self._segments[local_id] = seg
        return seg

    def add_grain(self,
                  grain: Grain,
                  segment_id: Optional[UUID] = None,
                  segment_local_id: Optional[int] = None):
        """Add a grain to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        self.add_grains((grain,), segment_id=segment_id, segment_local_id=segment_local_id)

    def add_grains(self,
                   grains: Iterable[Grain],
                   segment_id: Optional[UUID] = None,
                   segment_local_id: Optional[int] = None):
        """Add several grains to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        if self._open_encoder is not None:
            self._open_encoder.add_grains(grains, segment_id, segment_local_id)
        else:
            if segment_local_id is None:
                segments = sorted([
                    local_id for local_id in self._segments if
                    segment_id is None or self._segments[local_id].id == segment_id])
                if len(segments) > 0:
                    segment_local_id = segments[0]
            if segment_local_id is not None and segment_local_id in self._segments:
                segment = self._segments[segment_local_id]
            else:
                segment = self.add_segment(id=segment_id, local_id=segment_local_id)
            segment.add_grains(grains)

    @deprecated(version="2.7.0", reason="This mechanism is deprecated, use a context manager instead")
    def dump(self):
        """Dump the whole contents of this encoder to the file in one go,
        replacing anything that's already there."""
        self.start_dump(all_at_once=True)
        self.end_dump(all_at_once=True)

    @deprecated(version="2.7.0", reason="This mechanism is deprecated, use a context manager instead")
    def start_dump(self, all_at_once=False):
        """Start dumping the contents of this encoder to the specified file, if
        the file is seakable then it will replace the current content, otherwise
        it will append."""
        self._open_encoder = OpenGSFEncoder(self.file,
                                            self.major,
                                            self.minor,
                                            self.id,
                                            self.created,
                                            self._tags,
                                            self._segments,
                                            self.streaming,
                                            self._next_local)
        self._open_encoder._start_dump(all_at_once=all_at_once)

    @deprecated(version="2.7.0", reason="This mechanism is deprecated, use a context manager instead")
    def end_dump(self, all_at_once=False):
        """End the current dump to the file. In a seakable stream this will write
        all segment counts, in a non-seakable stream it will not."""
        if self._open_encoder is not None:
            self._open_encoder._end_dump()
            self._next_local = self._open_encoder._next_local
            self._open_encoder = None


class GSFEncoderFlow(NamedTuple):
    src_id: UUID
    flow_id: UUID
    format: str
    data: bytes


class GSFEncoderTag(object):
    """A class to represent a tag,

    has two properties:

    key
    value

    both strings."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    @property
    def encoded_key(self) -> bytes:
        return self.key.encode("utf-8")[:65535]

    @property
    def encoded_value(self) -> bytes:
        return self.value.encode("utf-8")[:65535]

    @property
    def tag_block_size(self) -> int:
        return 12 + len(self.encoded_key) + len(self.encoded_value)

    def __bytes__(self):
        return (
            b"tag " +
            _encode_uint(self.tag_block_size, 4) +
            _encode_uint(len(self.encoded_key), 2) +
            self.encoded_key +
            _encode_uint(len(self.encoded_value), 2) +
            self.encoded_value)

    def __eq__(self, other: object) -> bool:
        return other == (self.key, self.value)


class GSFEncoderSegment(object):
    """A class to represent a segment within a GSF file, used for constructing them."""

    def __init__(self,
                 id: UUID,
                 local_id: int,
                 tags: Optional[Iterable[Tuple[str, str]]] = None,
                 parent: Optional[Union[GSFEncoder, OpenGSFEncoderBase]] = None):
        self.id = id
        self.local_id = local_id
        self._write_count = 0
        self._count_pos = -1
        self._active_dump: bool = False
        self._tags: List[GSFEncoderTag] = []
        self._gsf_flow: Optional[GSFEncoderFlow] = None
        self._grains: List[Grain] = []
        self._parent = parent

        if tags is not None:
            for tag in tags:
                try:
                    self.add_tag(tag[0], tag[1])
                except (TypeError, IndexError):
                    raise GSFEncodeError("No idea how to turn {!r} into a tag".format(tag))

    def _get_parent_open_encoder(self) -> Optional[OpenGSFEncoder]:
        if isinstance(self._parent, OpenGSFEncoder):
            return self._parent
        elif isinstance(self._parent, GSFEncoder):
            return self._parent._open_encoder
        else:
            return None

    @property
    def count(self) -> int:
        return len(self._grains) + self._write_count

    @property
    def flow_block_size(self) -> int:
        if self._gsf_flow is None:
            return 0
        return 108 + len(self._gsf_flow.data)

    @property
    def segm_block_size(self) -> int:
        return 34 + self.flow_block_size + sum(tag.tag_block_size for tag in self._tags)

    @property
    def tags(self) -> Tuple[GSFEncoderTag, ...]:
        return tuple(self._tags)

    def get_write_count(self) -> int:
        return self._write_count

    def _encode_header(self, all_at_once: bool = False) -> Tuple[bytes, int]:
        self._active_dump = True
        data = (
            b"segm" +
            _encode_uint(self.segm_block_size, 4) +

            _encode_uint(self.local_id, 2) +
            _encode_uuid(self.id))
        count_pos = len(data)
        if all_at_once:
            data += _encode_sint(self.count, 8)
        else:
            data += _encode_sint(-1, 8)

        if self._gsf_flow is not None:
            data += (
                b"flow" +
                _encode_uint(self.flow_block_size, 4) +

                _encode_uuid(self._gsf_flow.src_id) +
                _encode_uuid(self._gsf_flow.flow_id) +
                (self._gsf_flow.format.encode("utf-8") + (b"\x00" * 64))[:64] +
                _encode_uint(len(self._gsf_flow.data), 4) +
                self._gsf_flow.data
            )

        for tag in self._tags:
            data += bytes(tag)

        return (data, count_pos)

    def set_size_position(self, pos: int):
        self._count_pos = pos

    def encode_all_grains(self) -> bytes:
        data = b''
        for grain in self._grains:
            data += self.encode_grain(grain)

        self._grains = []
        return data

    def encode_grain(self, grain: Grain) -> bytes:
        gbhd_size = self._gbhd_size_for_grain(grain)

        encode_ts_f = _encode_ts
        version_7_deprecated_bytes = b""
        if self._parent is not None and self._parent.major == 7:
            encode_ts_f = _encode_ts_v7
            version_7_deprecated_bytes = b"\x00"*16

        data = (
            b"grai" +
            _encode_uint(10 + gbhd_size + 8 + grain.length, 4) +
            _encode_uint(self.local_id, 2) +

            b"gbhd" +
            _encode_uint(gbhd_size, 4) +

            _encode_uuid(grain.source_id) +
            _encode_uuid(grain.flow_id) +
            version_7_deprecated_bytes +
            encode_ts_f(grain.origin_timestamp) +
            encode_ts_f(grain.sync_timestamp) +
            _encode_rational(grain.rate) +
            _encode_rational(grain.duration))

        if len(grain.timelabels) > 0:
            data += (
                b"tils" +
                _encode_uint(10 + 29*len(grain.timelabels), 4) +

                _encode_uint(len(grain.timelabels), 2))

            for label in grain.timelabels:
                tag = (label['tag'].encode('utf-8') + (b"\x00" * 16))[:16]
                data += (
                    tag +
                    _encode_uint(label['timelabel']['frames_since_midnight'], 4) +
                    _encode_uint(label['timelabel']['frame_rate_numerator'], 4) +
                    _encode_uint(label['timelabel']['frame_rate_denominator'], 4) +
                    _encode_uint(1 if label['timelabel']['drop_frame'] else 0, 1))

        if grain.grain_type == "video":
            data += self._encode_vghd_for_grain(cast(VideoGrain, grain))
        elif grain.grain_type == "coded_video":
            data += self._encode_cghd_for_grain(cast(CodedVideoGrain, grain))
        elif grain.grain_type == "audio":
            data += self._encode_aghd_for_grain(cast(AudioGrain, grain))
        elif grain.grain_type == "coded_audio":
            data += self._encode_cahd_for_grain(cast(CodedAudioGrain, grain))
        elif grain.grain_type == "event":
            data += self._encode_eghd_for_grain(cast(EventGrain, grain))
        elif grain.grain_type != "empty":  # pragma: no cover (should be unreachable)
            raise GSFEncodeError("Unknown grain type: {}".format(grain.grain_type))

        data += (
            b"grdt" +
            _encode_uint(8 + grain.length, 4))

        if grain.data is not None:
            data += bytes(grain.data)

        self._write_count += 1

        return data

    def _gbhd_size_for_grain(self, grain: Grain) -> int:
        size = 78
        if self._parent is not None and self._parent.major == 7:
            size += 16  # deprecated bytes
            size -= 2  # No sign byte in 2 x Timestamp
        if len(grain.timelabels) > 0:
            size += 10 + 29*len(grain.timelabels)
        if grain.grain_type == "video":
            size += self._vghd_size_for_grain(cast(VideoGrain, grain))
        elif grain.grain_type == "coded_video":
            size += self._cghd_size_for_grain(cast(CodedVideoGrain, grain))
        elif grain.grain_type == "audio":
            size += self._aghd_size_for_grain(cast(AudioGrain, grain))
        elif grain.grain_type == "coded_audio":
            size += self._cahd_size_for_grain(cast(CodedAudioGrain, grain))
        elif grain.grain_type == "event":
            size += self._eghd_size_for_grain(cast(EventGrain, grain))
        elif grain.grain_type != "empty":
            raise GSFEncodeError("Unknown grain type: {}".format(grain.grain_type))
        return size

    def _vghd_size_for_grain(self, grain: VideoGrain) -> int:
        size = 44
        if len(grain.components) > 0:
            size += 10 + 16*len(grain.components)
        return size

    def _encode_vghd_for_grain(self, grain: VideoGrain) -> bytes:
        data = (b"vghd" +
                _encode_uint(self._vghd_size_for_grain(grain), 4) +

                _encode_uint(int(grain.cog_frame_format), 4) +
                _encode_uint(int(grain.cog_frame_layout), 4) +
                _encode_uint(int(grain.width), 4) +
                _encode_uint(int(grain.height), 4) +
                _encode_uint(int(grain.extension), 4))

        if grain.source_aspect_ratio is None:
            data += _encode_rational(Fraction(0, 1))
        else:
            data += _encode_rational(grain.source_aspect_ratio)
        if grain.pixel_aspect_ratio is None:
            data += _encode_rational(Fraction(0, 1))
        else:
            data += _encode_rational(grain.pixel_aspect_ratio)

        if len(grain.components) > 0:
            data += (b"comp" +
                     _encode_uint(10 + 16*len(grain.components), 4) +

                     _encode_uint(len(grain.components), 2))

            for comp in grain.components:
                data += (_encode_uint(comp.width, 4) +
                         _encode_uint(comp.height, 4) +
                         _encode_uint(comp.stride, 4) +
                         _encode_uint(comp.length, 4))

        return data

    def _eghd_size_for_grain(self, grain: EventGrain) -> int:
        return 9

    def _encode_eghd_for_grain(self, grain: EventGrain) -> bytes:
        return (b"eghd" +
                _encode_uint(self._eghd_size_for_grain(grain), 4) +
                _encode_uint(0x00, 1))

    def _aghd_size_for_grain(self, grain: AudioGrain) -> int:
        return 22

    def _encode_aghd_for_grain(self, grain: AudioGrain) -> bytes:
        return (b"aghd" +
                _encode_uint(self._aghd_size_for_grain(grain), 4) +

                _encode_uint(int(grain.cog_audio_format), 4) +
                _encode_uint(int(grain.channels), 2) +
                _encode_uint(int(grain.samples), 4) +
                _encode_uint(int(grain.sample_rate), 4))

    def _cghd_size_for_grain(self, grain: CodedVideoGrain) -> int:
        size = 37
        if len(grain.unit_offsets) > 0:
            size += 10 + 4*len(grain.unit_offsets)
        return size

    def _encode_cghd_for_grain(self, grain: CodedVideoGrain) -> bytes:
        data = (b"cghd" +
                _encode_uint(self._cghd_size_for_grain(grain), 4) +

                _encode_uint(int(grain.cog_frame_format), 4) +
                _encode_uint(int(grain.cog_frame_layout), 4) +
                _encode_uint(int(grain.origin_width), 4) +
                _encode_uint(int(grain.origin_height), 4) +
                _encode_uint(int(grain.coded_width), 4) +
                _encode_uint(int(grain.coded_height), 4) +
                _encode_uint(int(grain.is_key_frame) if grain.is_key_frame is not None else 3, 1) +
                _encode_sint(int(grain.temporal_offset) if grain.temporal_offset is not None else 0x7fffffff, 4))

        if len(grain.unit_offsets) > 0:
            data += (b"unof" +
                     _encode_uint(10 + 4*len(grain.unit_offsets), 4) +
                     _encode_uint(len(grain.unit_offsets), 2))

            for i in range(0, len(grain.unit_offsets)):
                data += _encode_uint(grain.unit_offsets[i], 4)

        return data

    def _cahd_size_for_grain(self, grain: CodedAudioGrain) -> int:
        return 30

    def _encode_cahd_for_grain(self, grain: CodedAudioGrain) -> bytes:
        return (b"cahd" +
                _encode_uint(self._cahd_size_for_grain(grain), 4) +

                _encode_uint(int(grain.cog_audio_format), 4) +
                _encode_uint(int(grain.channels), 2) +
                _encode_uint(int(grain.samples), 4) +
                _encode_uint(int(grain.priming), 4) +
                _encode_uint(int(grain.remainder), 4) +
                _encode_uint(int(grain.sample_rate), 4))

    def add_tag(self, key: str, value: str):
        """Add a tag to the segment"""
        if self._active_dump:
            raise GSFEncodeAddToActiveDump("Cannot add a tag to a segment which is part of an active export")
        self._tags.append(GSFEncoderTag(key, value))

    def add_flow(self, src_id: UUID, flow_id: UUID, format: str, data: str | bytes) -> None:
        """Add flow metadata to the segment

        :param src_id: The source ID for the flow
        :param flow_id: The flow ID
        :param format: The flow format URN
        :param data: The flow metadata JSON string or bytes
        """
        if self._active_dump:
            raise GSFEncodeAddToActiveDump("Cannot add a 'flow' to a segment which is part of an active export")
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._gsf_flow = GSFEncoderFlow(src_id=src_id, flow_id=flow_id, format=format, data=data)

    def add_grain(self, grain: Grain):
        """Add a grain to the segment, which should be a Grain object"""
        parent = self._get_parent_open_encoder()
        if parent is not None and parent._active_dump:
            parent.add_grain(grain, segment_id=self.id, segment_local_id=self.local_id)
        else:
            self._grains.append(grain)

    def add_grains(self, grains: Iterable[Grain]):
        """Add several grains to the segment, the parameter should be an
        iterable of grain objects"""
        parent = self._get_parent_open_encoder()
        if parent is not None and parent._active_dump:
            parent.add_grains(grains, segment_id=self.id, segment_local_id=self.local_id)
        else:
            for grain in grains:
                self.add_grain(grain)
