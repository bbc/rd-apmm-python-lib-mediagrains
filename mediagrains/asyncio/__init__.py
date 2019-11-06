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
Library for handling mediagrains in pure python asyncio compatibility layer.

THIS SUBLIBRARY IS DEPRECATED.

DO NOT USE IT IN NEW WORK, IT WILL SOON BE REMOVED.

THE ASYNCIO CAPABILITIES ARE NOW INCLUDED IN mediagrains.gsf
"""

from deprecated import deprecated

import asyncio

from uuid import UUID
from os import SEEK_SET
from datetime import datetime
from fractions import Fraction

from mediatimestamp.immutable import Timestamp

from .aiobytes import AsyncIOBytes, AsyncLazyLoaderUnloadedError
from .bytesaio import BytesAIO

from mediagrains import Grain
from mediagrains.gsf import GSFDecodeBadVersionError, GSFDecodeBadFileTypeError, GSFDecodeError

__all__ = ["AsyncGSFDecoder", "AsyncLazyLoaderUnloadedError", "loads"]


@deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
async def loads(s, cls=None, parse_grain=None, **kwargs):
    """Deserialise a GSF file from a string (or similar) into python,
    returns a pair of (head, segments) where head is a python dict
    containing general metadata from the file, and segments is a dictionary
    mapping numeric segment ids to lists of Grain objects.

    If you wish to use a custom AsyncGSFDecoder subclass pass it as cls, if you
    wish to use a custom Grain constructor pass it as parse_grain. The
    defaults are AsyncGSFDecoder and Grain. Extra kwargs will be passed to the
    decoder constructor.

    The custome parse_grain method can be an asynchronous coroutine or a synchronous callable.

    There is no real benefit to using this over the synchronous version, since access to an in-memory buffer is
    always going to be synchronous, but this can be used for convenience where you don't want multiple code paths
    for synchronous and asynchronous code."""
    if cls is None:
        cls = AsyncGSFDecoder
    if parse_grain is None:
        parse_grain = Grain
    dec = cls(BytesAIO(s), parse_grain=parse_grain, **kwargs)
    return await dec.decode()


class AsyncGSFBlock():
    """A single block in a GSF file, accessed asynchronously

    Has coroutines to read various types from the block.
    Must be used as an asynchronous context manager, which will automatically decode the block tag and size,
    exposed by the `tag` and `size` attributes.
    """
    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    def __init__(self, file_data, want_tag=None, raise_on_wrong_tag=False):
        """Constructor. Unlike the synchronous version does not record the start byte of the block in `block_start`

        :param file_data: An asynchronous readable file-like object positioned at the start of the block
        :param want_tag: If set to a tag string, and in a context manager, skip any block without that tag
        :param raise_on_wrong_tag: Set to True to raise a GSFDecodeError if the next block isn't `want_tag`
        """
        self.file_data = file_data
        self.want_tag = want_tag
        self.raise_on_wrong_tag = raise_on_wrong_tag

        self.size = None
        self.block_start = None

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def __aenter__(self):
        """When used as a context manager record file position and read block size and tag on entry

        - When entering a block, tag and size should be read
        - If tag doesn't decode, a GSFDecodeError should be raised
        - If want_tag was supplied to the constructor, skip blocks that don't have that tag
        - Unless raise_on_wrong_tag was also supplied, in which case raise

        :returns: Instance of AsyncGSFBlock
        :raises GSFDecodeError: If the block tag failed to decode as UTF-8, or an unwanted tag was found"""

        self.block_start = await self.file_data.tell()  # In binary mode, this should always be in bytes

        while True:
            tag_bytes = await self.file_data.read(4)

            try:
                self.tag = tag_bytes.decode(encoding="utf-8")
            except UnicodeDecodeError:
                raise GSFDecodeError(
                    "Bytes {!r} at location {} do not make a valid tag for a block".format(tag_bytes, self.block_start),
                    self.block_start
                )

            self.size = await self.read_uint(4)

            if self.want_tag is None or self.tag == self.want_tag:
                return self
            elif self.tag != self.want_tag and self.raise_on_wrong_tag:
                raise GSFDecodeError("Wanted tag {} but got {} at {}".format(self.want_tag, self.tag, self.block_start),
                                     self.block_start)
            else:
                await self.file_data.seek(self.block_start + self.size, SEEK_SET)
                self.block_start = await self.file_data.tell()

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def __aexit__(self, *args):
        """When used as a context manager, exiting context should seek to the block end"""
        await self.file_data.seek(self.block_start + self.size, SEEK_SET)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def has_child_block(self, strict_blocks=True):
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

        bytes_remaining = await self.get_remaining()
        if bytes_remaining >= 8:
            return True
        elif bytes_remaining != 0 and strict_blocks:
            position = await self.file_data.tell()
            raise GSFDecodeError("Found a partial block (or parent too small) in '{}' at {}".format(self.tag, position),
                                 position)
        else:
            return False

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def child_blocks(self, strict_blocks=True):
        """Asynchronous generator for each child block - each yielded block sits within the context manager

        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :yields: GSFBlock for child (already acting as a context manager)
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        while await self.has_child_block(strict_blocks=strict_blocks):
            async with AsyncGSFBlock(self.file_data) as child_block:
                yield child_block

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def get_remaining(self):
        """Get the number of bytes left in this block

        Only works in a context manager, will raise an AssertionError if not

        :returns: Number of bytes left in the block
        """
        assert self.size is not None, "get_remaining() only works in a context manager"
        return (self.block_start + self.size) - await self.file_data.tell()

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_uint(self, length):
        """Read an unsigned integer of length `length`

        :param length: Number of bytes used to store the integer
        :returns: Unsigned integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = 0
        uint_bytes = bytes(await self.file_data.read(length))

        if len(uint_bytes) != length:
            raise EOFError("Unable to read enough bytes from source")

        for n in range(0, length):
            r += (uint_bytes[n] << (n*8))
        return r

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_bool(self):
        """Read a boolean value

        :returns: Boolean value
        :raises EOFError: If there are no more bytes left in the source"""
        n = await self.read_uint(1)
        return (n != 0)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_sint(self, length):
        """Read a 2's complement signed integer

        :param length: Number of bytes used to store the integer
        :returns: Signed integer
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        r = await self.read_uint(length)
        if (r >> ((8*length) - 1)) == 1:
            r -= (1 << (8*length))
        return r

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_string(self, length):
        """Read a fixed-length string, treating it as UTF-8

        :param length: Number of bytes in the string
        :returns: String
        :raises EOFError: If there are fewer than `length` bytes left in the source
        """
        string_data = await self.file_data.read(length)
        if (len(string_data) != length):
            raise EOFError("Unable to read enough bytes from source")

        return string_data.decode(encoding='utf-8')

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_varstring(self):
        """Read a variable length string

        Reads a 2 byte uint to get the string length, then reads a string of that length

        :returns: String
        :raises EOFError: If there are too few bytes left in the source
        """
        length = await self.read_uint(2)
        return await self.read_string(length)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_uuid(self):
        """Read a UUID

        :returns: UUID
        :raises EOFError: If there are fewer than l bytes left in the source
        """
        uuid_data = await self.file_data.read(16)

        if (len(uuid_data) != 16):
            raise EOFError("Unable to read enough bytes from source")

        return UUID(bytes=uuid_data)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_timestamp(self):
        """Read a date-time (with seconds resolution) stored in 7 bytes

        :returns: Datetime
        :raises EOFError: If there are fewer than 7 bytes left in the source
        """
        year = await self.read_sint(2)
        month = await self.read_uint(1)
        day = await self.read_uint(1)
        hour = await self.read_uint(1)
        minute = await self.read_uint(1)
        second = await self.read_uint(1)
        return datetime(year, month, day, hour, minute, second)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_ippts(self):
        """Read a mediatimestamp.Timestamp

        :returns: Timestamp
        :raises EOFError: If there are fewer than 10 bytes left in the source
        """
        secs = await self.read_uint(6)
        nano = await self.read_uint(4)
        return Timestamp(secs, nano)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def read_rational(self):
        """Read a rational (fraction)

        If numerator or denominator is 0, returns Fraction(0)

        :returns: fraction.Fraction
        :raises EOFError: If there are fewer than 8 bytes left in the source
        """
        numerator = await self.read_uint(4)
        denominator = await self.read_uint(4)
        if numerator == 0 or denominator == 0:
            return Fraction(0)
        else:
            return Fraction(numerator, denominator)


@deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
def asynchronise(f):
    async def __inner(*args, **kwargs):
        return f(*args, **kwargs)
    return __inner


class AsyncGSFDecoder(object):
    """A decoder for GSF format that operates asynchronously.

    Provides coroutines to decode the header of a GSF file, followed by an asynchronous generator to get each grain,
    wrapped in some grain method (mediagrains.Grain by default.)
    """
    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    def __init__(self, file_data, parse_grain=Grain, **kwargs):
        """Constructor

        :param parse_grain: Function or coroutine that takes a (metadata dict, buffer) and returns a grain
                            representation
        :param file_data: A readable asynchronous file io-like object similar to those provided by aiofiles
        """
        self.Grain = parse_grain
        if not asyncio.iscoroutine(self.Grain):
            self.Grain = asynchronise(self.Grain)
        self.file_data = file_data
        self.head = None
        self.start_loc = None

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def _decode_ssb_header(self):
        """Find and read the SSB header in the GSF file

        :returns: (major, minor) version tuple
        :raises GSFDecodeBadFileTypeError: If the SSB tag shows this isn't a GSF file
        """

        ssb_block = AsyncGSFBlock(self.file_data)
        ssb_block.block_start = await self.file_data.tell()
        tag = await ssb_block.read_string(8)

        if tag != "SSBBgrsg":
            raise GSFDecodeBadFileTypeError("File lacks correct header", ssb_block.block_start, tag)

        major = await ssb_block.read_uint(2)
        minor = await ssb_block.read_uint(2)

        return (major, minor)

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def _decode_head(self, head_block):
        """Decode the "head" block and extract ID, created date, segments and tags

        :param head_block: AsyncGSFBlock representing the "head" block
        :returns: Head block as a dict
        """
        head = {}
        head['id'] = await head_block.read_uuid()
        head['created'] = await head_block.read_timestamp()

        head['segments'] = []
        head['tags'] = []

        # Read head block children
        async for head_child in head_block.child_blocks():
            # Parse a segment block
            if head_child.tag == "segm":
                segm = {}
                segm['local_id'] = await head_child.read_uint(2)
                segm['id'] = await head_child.read_uuid()
                segm['count'] = await head_child.read_sint(8)
                segm['tags'] = []

                # Segment blocks can have child tags as well
                while await head_child.has_child_block():
                    async with AsyncGSFBlock(self.file_data) as segm_tag:
                        if segm_tag.tag == "tag ":
                            key = await segm_tag.read_varstring()
                            value = await segm_tag.read_varstring()
                            segm['tags'].append((key, value))

                head['segments'].append(segm)

            # Parse a tag block
            elif head_child.tag == "tag ":
                key = await head_child.read_varstring()
                value = await head_child.read_varstring()
                head['tags'].append((key, value))

        return head

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def _decode_tils(self, tils_block):
        """Decode timelabels (tils) block

        :param tils_block: Instance of AsyncGSFBlock() representing a "gbhd" block
        :returns: tils block as a dict
        """
        tils = []
        timelabel_count = await tils_block.read_uint(2)
        for i in range(0, timelabel_count):
            tag = await tils_block.read_string(16)
            tag = tag.strip("\x00")
            count = await tils_block.read_uint(4)
            rate = await tils_block.read_rational()
            drop = await tils_block.read_bool()

            tils.append({'tag': tag,
                         'timelabel': {'frames_since_midnight': count,
                                       'frame_rate_numerator': rate.numerator,
                                       'frame_rate_denominator': rate.denominator,
                                       'drop_frame': drop}})

        return tils

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def _decode_gbhd(self, gbhd_block):
        """Decode grain block header ("gbhd") to get grain metadata

        :param gbhd_block: Instance of AsyncGSFBlock() representing a "gbhd" block
        :returns: Grain data dict
        :raises GSFDecodeError: If "gbhd" block contains an unkown child block
        """
        meta = {
            "grain": {
            }
        }

        meta['grain']['source_id'] = await gbhd_block.read_uuid()
        meta['grain']['flow_id'] = await gbhd_block.read_uuid()
        await self.file_data.seek(16, 1)  # Skip over deprecated byte array
        meta['grain']['origin_timestamp'] = await gbhd_block.read_ippts()
        meta['grain']['sync_timestamp'] = await gbhd_block.read_ippts()
        meta['grain']['rate'] = await gbhd_block.read_rational()
        meta['grain']['duration'] = await gbhd_block.read_rational()

        async for gbhd_child in gbhd_block.child_blocks():
            if gbhd_child.tag == "tils":
                meta['grain']['timelabels'] = await self._decode_tils(gbhd_child)
            elif gbhd_child.tag == "vghd":
                meta['grain']['grain_type'] = 'video'
                meta['grain']['cog_frame'] = {}
                meta['grain']['cog_frame']['format'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['layout'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['width'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['height'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_frame']['extension'] = await gbhd_child.read_uint(4)

                src_aspect_ratio = await gbhd_child.read_rational()
                if src_aspect_ratio != 0:
                    meta['grain']['cog_frame']['source_aspect_ratio'] = {
                        'numerator': src_aspect_ratio.numerator,
                        'denominator': src_aspect_ratio.denominator
                    }

                pixel_aspect_ratio = await gbhd_child.read_rational()
                if pixel_aspect_ratio != 0:
                    meta['grain']['cog_frame']['pixel_aspect_ratio'] = {
                        'numerator': pixel_aspect_ratio.numerator,
                        'denominator': pixel_aspect_ratio.denominator
                    }

                meta['grain']['cog_frame']['components'] = []
                if await gbhd_child.has_child_block():
                    async with AsyncGSFBlock(self.file_data) as comp_block:
                        if comp_block.tag != "comp":
                            continue  # Skip unknown/unexpected block

                        comp_count = await comp_block.read_uint(2)
                        offset = 0
                        for i in range(0, comp_count):
                            comp = {}
                            comp['width'] = await comp_block.read_uint(4)
                            comp['height'] = await comp_block.read_uint(4)
                            comp['stride'] = await comp_block.read_uint(4)
                            comp['length'] = await comp_block.read_uint(4)
                            comp['offset'] = offset
                            offset += comp['length']
                            meta['grain']['cog_frame']['components'].append(comp)

            elif gbhd_child.tag == 'cghd':
                meta['grain']['grain_type'] = "coded_video"
                meta['grain']['cog_coded_frame'] = {}
                meta['grain']['cog_coded_frame']['format'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['layout'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['origin_width'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['origin_height'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['coded_width'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['coded_height'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_frame']['is_key_frame'] = await gbhd_child.read_bool()
                meta['grain']['cog_coded_frame']['temporal_offset'] = await gbhd_child.read_sint(4)

                if await gbhd_child.has_child_block():
                    async with AsyncGSFBlock(self.file_data) as unof_block:
                        meta['grain']['cog_coded_frame']['unit_offsets'] = []

                        unit_offsets = await unof_block.read_uint(2)
                        for i in range(0, unit_offsets):
                            meta['grain']['cog_coded_frame']['unit_offsets'].append(await unof_block.read_uint(4))

            elif gbhd_child.tag == "aghd":
                meta['grain']['grain_type'] = "audio"
                meta['grain']['cog_audio'] = {}
                meta['grain']['cog_audio']['format'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_audio']['channels'] = await gbhd_child.read_uint(2)
                meta['grain']['cog_audio']['samples'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_audio']['sample_rate'] = await gbhd_child.read_uint(4)

            elif gbhd_child.tag == "cahd":
                meta['grain']['grain_type'] = "coded_audio"
                meta['grain']['cog_coded_audio'] = {}
                meta['grain']['cog_coded_audio']['format'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['channels'] = await gbhd_child.read_uint(2)
                meta['grain']['cog_coded_audio']['samples'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['priming'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['remainder'] = await gbhd_child.read_uint(4)
                meta['grain']['cog_coded_audio']['sample_rate'] = await gbhd_child.read_uint(4)

            elif gbhd_child.tag == "eghd":
                meta['grain']['grain_type'] = "event"
            else:
                raise GSFDecodeError(
                    "Unknown type {} at offset {}".format(gbhd_child.tag, gbhd_child.block_start),
                    gbhd_child.block_start,
                    length=gbhd_child.size
                )

        return meta

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def decode_file_headers(self):
        """Verify the file is a supported version, and get the file header

        :returns: File header data (segments and tags) as a dict
        :raises GSFDecodeBadVersionError: If the file version is not supported
        :raises GSFDecodeBadFileTypeError: If this isn't a GSF file
        :raises GSFDecodeError: If the file doesn't have a "head" block
        """
        if self.head is not None:
            return self.head

        (major, minor) = await self._decode_ssb_header()
        if (major, minor) != (7, 0):
            raise GSFDecodeBadVersionError("Unknown Version {}.{}".format(major, minor), 0, major, minor)

        try:
            async with AsyncGSFBlock(self.file_data, want_tag="head") as head_block:
                self.head = await self._decode_head(head_block)
                return self.head
        except EOFError:
            raise GSFDecodeError("No head block found in file", await self.file_data.tell())

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def __aenter__(self):
        if self.start_loc is None:
            self.start_loc = await self.file_data.tell()
        await self.decode_file_headers()
        return self

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def __aexit__(self, *args, **kwargs):
        if self.start_loc is not None:
            await self.file_data.seek(self.start_loc)
            self.start_loc = None

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    def __aiter__(self):
        return self.grains()

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def grains(self, local_ids=None, load_lazily=True):
        """Asynchronous generator to get grains from the GSF file. Skips blocks which aren't "grai".

        The file_data will be positioned after the `grai` block.

        :param local_ids: A list of local-ids to include in the output. If None (the default) then all local-ids will be
                          included
        :param skip_data: If True, grain data blocks will be seeked over and only grain headers will be read
        :param load_lazily: If True, the grains returned will be designed to lazily load data from the underlying stream
                            only when it is needed. These grain data elements will have an extra 'load' coroutine for
                            triggering this load, and accessing data in their data element without first awaiting this
                            coroutine will raise an exception.
        :yields: (Grain, local_id) tuple for each grain
        :raises GSFDecodeError: If grain is invalid (e.g. no "gbhd" child)
        """
        await self.decode_file_headers()

        while True:
            try:
                async with AsyncGSFBlock(self.file_data, want_tag="grai") as grai_block:
                    if grai_block.size == 0:
                        return  # Terminator block reached

                    local_id = await grai_block.read_uint(2)

                    if local_ids is not None and local_id not in local_ids:
                        continue

                    async with AsyncGSFBlock(self.file_data, want_tag="gbhd", raise_on_wrong_tag=True) as gbhd_block:
                        meta = await self._decode_gbhd(gbhd_block)

                    data = None

                    if await grai_block.has_child_block():
                        async with AsyncGSFBlock(self.file_data, want_tag="grdt") as grdt_block:
                            if await grdt_block.get_remaining() > 0:
                                if load_lazily:
                                    data = AsyncIOBytes(self.file_data,
                                                        await self.file_data.tell(),
                                                        await grdt_block.get_remaining())
                                else:
                                    data = await self.file_data.read(await grdt_block.get_remaining())

                yield (await self.Grain(meta, data), local_id)
            except EOFError:
                return  # We ran out of grains to read and hit EOF

    @deprecated(version="2.7.0", reason="Asyncio is now supported directly in mediagrains.gsf")
    async def decode(self, load_lazily=False):
        """Decode a GSF formatted bytes object

        :param load_lazily: If True, the grains returned will be designed to lazily load data from the underlying stream
                            only when it is needed. These grain data elements will have an extra 'load' coroutine for
                            triggering this load, and accessing data in their data element without first awaiting this
                            coroutine will raise an exception.
        :returns: A dictionary mapping sequence ids to lists of GRAIN objects (or subclasses of such).
        """
        segments = {}
        async with self:
            async for (grain, local_id) in self.grains(load_lazily=load_lazily):
                if local_id not in segments:
                    segments[local_id] = []
                segments[local_id].append(grain)

            return (self.head, segments)
