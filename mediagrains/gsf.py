#!/usr/bin/python
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
"""

from __future__ import print_function, absolute_import
from . import Grain
from six import indexbytes
from uuid import UUID, uuid1
from datetime import datetime
from nmoscommon.timestamp import Timestamp
from fractions import Fraction
from frozendict import frozendict
from six import BytesIO, PY3

__all__ = ["GSFDecoder", "load", "loads", "GSFError", "GSFDecodeError",
           "GSFDecodeBadFileTypeError", "GSFDecodeBadVersionError",
           "GSFEncoder", "dump", "dumps", "GSFEncodeError",
           "GSFEncodeAddToActiveDump"]


def loads(s, cls=None, parse_grain=None, **kwargs):
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
        parse_grain = Grain
    dec = cls(parse_grain=parse_grain, **kwargs)
    return dec.decode(s)


def load(fp, cls=None, parse_grain=None, **kwargs):
    """Deserialise a GSF file from a file object (or similar) into python,
    returns a pair of (head, segments) where head is a python dict
    containing general metadata from the file, and segments is a dictionary
    mapping numeric segment ids to lists of Grain objects.

    If you wish to use a custom GSFDecoder subclass pass it as cls, if you
    wish to use a custom Grain constructor pass it as parse_grain. The
    defaults are GSFDecoder and Grain. Extra kwargs will be passed to the
    decoder constructor."""
    s = fp.read()
    return loads(s, cls=cls, parse_grain=parse_grain, **kwargs)


def dump(grains, fp, cls=None, segment_tags=None, **kwargs):
    """Serialise a series of grains into a GSF file.

    :param grains an iterable of grain objects
    :param fp a ByteIO-like object to write to
    :param segment_tags a list of pairs of strings to use as tags for the segment created
    :param cls the class to use for encoding, GSFEncoder is the default

    other keyword arguments will be fed to the class constructor.

    This method will serialise the grains in a single segment."""
    if cls is None:
        cls = GSFEncoder
    enc = cls(fp, **kwargs)
    seg = enc.add_segment(tags=segment_tags)
    seg.add_grains(grains)
    enc.dump()


def dumps(grains, cls=None, segment_tags=None, **kwargs):
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
    """The version was not 7.0

    properties:

    major
        The major version detected

    minor
        The minor version detected"""
    def __init__(self, msg, i, major, minor):
        super(GSFDecodeBadVersionError, self).__init__(msg, i, 8)
        self.major = major
        self.minor = minor


class GSFBlock():
    """Context manager for a single block in a GSF file

    Decodes the tag and size of the block
    """
    def __init__(self, file_data):
        self.file_data = file_data
        self.size = None
        self.block_start = self.file_data.tell()  # In binary mode, this should always be in bytes

    def __enter__(self):
        try:
            self.tag = self.read_string(4)
        except UnicodeDecodeError:
            self.file_data.seek(-4, 1)
            bad_bytes = self.file_data.read(4)
            position = self.file_data.tell() - 4
            raise GSFDecodeError(
                "Bytes {!r} at location {} do not make a valid tag for a block".format(
                    bad_bytes, position),
                position)

        self.size = self.read_uint(4)
        return self

    def __exit__(self, *args):
        self.file_data.seek(self.block_start + self.size, 0)  # TODO: Real constant

    def has_child_block(self, strict_blocks=True):
        """Checks if there is space for another child block in this block

        Returns true if there is space for another child block (i.e. > 8 bytes) in this block.
        If strict_blocks=True, this block only contains other blocks rather than any other data. As a result, if there
        are bytes left, but not enough for another block, raise a GSFDecodeError.
        Must be used in a context manager.

        :param strict_blocks: Set to True to raise if a partial block is found
        :returns: True if there is spaces for another block
        :raises GSFDecodeError: If there is a partial block and strict=True
        """
        assert self.size is not None, "in_block() only works in a context manager"

        bytes_remaining = self.get_remaining()
        if bytes_remaining >= 8:
            return True
        elif bytes_remaining != 0 and strict_blocks:
            position = self.file_data.tell()
            raise GSFDecodeError("Found a partial block (or parent too small) in '{}' at {}".format(self.tag, position),
                                 position)
        else:
            return False

    def get_remaining(self):
        """Returns number of bytes left in this block. Only works in a context manager"""
        assert self.size is not None, "get_remaining() only works in a context manager"
        return (self.block_start + self.size) - self.file_data.tell()

    def read_uint(self, l):
        r = 0
        uint_bytes = bytes(self.file_data.read(l))

        if len(uint_bytes) != l:
            raise EOFError("Unable to read enough bytes from source")

        for n in range(0, l):
            r += (indexbytes(uint_bytes, n) << (n*8))
        return r

    def read_bool(self):
        n = self.read_uint(1)
        return (n != 0)

    def read_sint(self, l):
        r = self.read_uint(l)
        if (r >> ((8*l) - 1)) == 1:
            r -= (1 << (8*l))
        return r

    def read_string(self, l):
        string_data = self.file_data.read(l)
        if (len(string_data) != l):
            raise EOFError("Unable to read enough bytes from source")

        return string_data.decode(encoding='utf-8')

    def read_varstring(self):
        length = self.read_uint(2)
        return self.read_string(length)

    def read_uuid(self):
        uuid_data = self.file_data.read(16)

        if (len(uuid_data) != 16):
            raise EOFError("Unable to read enough bytes from source")

        return UUID(bytes=uuid_data)

    def read_timestamp(self):
        year = self.read_sint(2)
        month = self.read_uint(1)
        day = self.read_uint(1)
        hour = self.read_uint(1)
        minute = self.read_uint(1)
        second = self.read_uint(1)
        return datetime(year, month, day, hour, minute, second)

    def read_ippts(self):
        secs = self.read_uint(6)
        nano = self.read_uint(4)
        return Timestamp(secs, nano)

    def read_rational(self):
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


class GSFDecoder(object):
    """A decoder for GSF format.

    Constructor takes a single optional argument parse_grain,
    which should be a function which takes a metadata dictionary
    and a buffer object and returns some sort of object representing
    a grain. The default is to use the function Grain.

    The only public method is "decode", which takes a string (or similar)
    as an argument and returns a pair of a dictionary of file metadata and a
    dictionary mapping numeric segment ids to lists of grain objects."""
    def __init__(self, parse_grain=Grain, **kwargs):
        self.Grain = parse_grain

    def _read_uint(self, b, i, l):
        r = 0
        for n in range(0, l):
            r += (indexbytes(b, i+n) << (n*8))
        return (r, i+l)

    def _read_bool(self, b, i):
        (n, i) = self._read_uint(b, i, 1)
        return ((n != 0), i)

    def _read_sint(self, b, i, l):
        (r, i) = self._read_uint(b, i, l)
        if (r >> ((8*l) - 1)) == 1:
            r -= (1 << (8*l))
        return (r, i)

    def _read_string(self, b, i, l):
        return (b[i:i+l].decode(encoding='utf-8'), i+l)

    def _read_varstring(self, b, i):
        (l, i) = self._read_uint(b, i, 2)
        return (self._read_string(b, i, l)[0], i+l)

    def _read_uuid(self, b, i):
        return (UUID(bytes=b[i:i+16]), i+16)

    def _read_timestamp(self, b, i):
        (year, i) = self._read_sint(b, i, 2)
        (month, i) = self._read_uint(b, i, 1)
        (day, i) = self._read_uint(b, i, 1)
        (hour, i) = self._read_uint(b, i, 1)
        (minute, i) = self._read_uint(b, i, 1)
        (second, i) = self._read_uint(b, i, 1)
        return (datetime(year, month, day, hour, minute, second), i)

    def _read_ippts(self, b, i):
        (secs, i) = self._read_uint(b, i, 6)
        (nano, i) = self._read_uint(b, i, 4)
        return (Timestamp(secs, nano), i)

    def _read_rational(self, b, i):
        (numerator, i) = self._read_uint(b, i, 4)
        (denominator, i) = self._read_uint(b, i, 4)
        if numerator == 0:
            return (Fraction(0), i)
        else:
            return (Fraction(numerator, denominator), i)

    def _decode_ssb_header(self, b, i):
        start = i
        (tag, i) = self._read_string(b, i, 8)
        if tag != "SSBBgrsg":
            raise GSFDecodeBadFileTypeError("File lacks correct header", start, tag)
        (major, i) = self._read_uint(b, i,  2)
        (minor, i) = self._read_uint(b, i, 2)
        return (major, minor, i)

    def _decode_block_header(self, b, i, allowed=None, optional=False):
        start = i
        while i <= len(b) - 8:
            try:
                (tag, i) = self._read_string(b, i, 4)
            except UnicodeDecodeError:
                raise GSFDecodeError("Bytes {!r} at location {} do not make a valid tag for a block".format(b[i:i+4], i), i, 4)
            (size, i) = self._read_uint(b, i, 4)
            if allowed is None or tag in allowed:
                return (tag, size, i)
            elif optional:
                return ("", 0, start)
        return ("", 0, start)

    def _decode_head(self, b, i):
        start = i
        head = {}

        (tag, size, i) = self._decode_block_header(b, i, ["head"])
        if tag == "":
            raise GSFDecodeError("No head block found in file", i)
        head_start = i - 8
        (head['id'], i) = self._read_uuid(b, i)
        (head['created'], i) = self._read_timestamp(b, i)
        head['segments'] = []
        head['tags'] = []

        head_end = head_start + size
        while i < head_end:
            (tag, size, i) = self._decode_block_header(b, i, ["segm", "tag "])
            if tag == "":
                i = head_end
                break
            segm_start = i - 8
            segm_end = segm_start + size
            if tag == "tag ":
                (key, i) = self._read_varstring(b, i)
                (val, i) = self._read_varstring(b, i)
                head['tags'].append((key, val))
            else:
                segm = {}
                (segm['local_id'], i) = self._read_uint(b, i, 2)
                (segm['id'], i) = self._read_uuid(b, i)
                (segm['count'], i) = self._read_sint(b, i, 8)
                segm['tags'] = []

                while i < segm_end:
                    (tag, size, i) = self._decode_block_header(b, i, ["tag "])
                    if tag != "":
                        (key, i) = self._read_varstring(b, i)
                        (val, i) = self._read_varstring(b, i)
                        segm['tags'].append((key, val))
                head['segments'].append(segm)

            if i > segm_end:
                raise GSFDecodeError("Size of segm block not large enough to contain its contents", segm_start, length=segm_end - segm_start)

        if i != head_end:
            raise GSFDecodeError("Size of head block not large enough to contain its contents", start, length=head_end - start)

        return (head, i)

    def _decode_tils(self, b, i):
        tils = []
        (n, i) = self._read_uint(b, i, 2)
        for k in range(0, n):
            (tag, i) = self._read_string(b, i, 16)
            tag = tag.strip('\x00')
            (count, i) = self._read_uint(b, i, 4)
            (rate, i) = self._read_rational(b, i)
            (drop, i) = self._read_bool(b, i)
            tils.append({'tag': tag,
                         'timelabel': {'frames_since_midnight': count,
                                       'frame_rate_numerator': rate.numerator,
                                       'frame_rate_denominator': rate.denominator,
                                       'drop_frame': drop}})
        return (tils, i)

    def _decode_gbhd(self, b, i):
        start = i
        meta = {
            "grain": {
            }
        }
        (_, size, i) = self._decode_block_header(b, i, ["gbhd"])
        gbhd_end = start + size
        (meta['grain']['source_id'], i) = self._read_uuid(b, i)
        (meta['grain']['flow_id'], i) = self._read_uuid(b, i)
        i += 16
        (meta['grain']['origin_timestamp'], i) = self._read_ippts(b, i)
        (meta['grain']['sync_timestamp'], i) = self._read_ippts(b, i)
        (meta['grain']['rate'], i) = self._read_rational(b, i)
        (meta['grain']['duration'], i) = self._read_rational(b, i)

        block_start = i
        (tag, size, i) = self._decode_block_header(b, i, ["tils"], optional=True)
        block_end = block_start + size
        if size != 0:
            (meta['grain']['timelabels'], i) = self._decode_tils(b, i)

        if i == gbhd_end:
            meta['grain']['grain_type'] = 'empty'
            block_end = i
        else:
            (tag, size, i) = self._decode_block_header(b, i, ['vghd', 'cghd', 'aghd', 'cahd', 'eghd'])
            block_start = i - 8
            block_end = block_start + size

            if tag == "vghd":
                meta['grain']['grain_type'] = 'video'
                meta['grain']['cog_frame'] = {}
                (meta['grain']['cog_frame']['format'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_frame']['layout'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_frame']['width'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_frame']['height'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_frame']['extension'], i) = self._read_uint(b, i, 4)
                (ar, i) = self._read_rational(b, i)
                if ar != 0:
                    meta['grain']['cog_frame']['source_aspect_ratio'] = {'numerator': ar.numerator,
                                                                         'denominator': ar.denominator}
                (ar, i) = self._read_rational(b, i)
                if ar != 0:
                    meta['grain']['cog_frame']['pixel_aspect_ratio'] = {'numerator': ar.numerator,
                                                                        'denominator': ar.denominator}
                meta['grain']['cog_frame']['components'] = []
                if i < block_end:
                    comp_start = i
                    (tag, size, i) = self._decode_block_header(b, i, ["comp"], optional=True)
                    comp_end = comp_start + size
                    if size != 0:
                        (n_comps, i) = self._read_uint(b, i, 2)
                        offset = 0
                        for c in range(0, n_comps):
                            comp = {}
                            (comp['width'], i) = self._read_uint(b, i, 4)
                            (comp['height'], i) = self._read_uint(b, i, 4)
                            (comp['stride'], i) = self._read_uint(b, i, 4)
                            (comp['length'], i) = self._read_uint(b, i, 4)
                            comp['offset'] = offset
                            offset += comp['length']
                            meta['grain']['cog_frame']['components'].append(comp)
                    i = comp_end
            elif tag == 'cghd':
                meta['grain']['grain_type'] = "coded_video"
                meta['grain']['cog_coded_frame'] = {}
                (meta['grain']['cog_coded_frame']['format'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['layout'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['origin_width'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['origin_height'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['coded_width'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['coded_height'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_frame']['is_key_frame'], i) = self._read_bool(b, i)
                (meta['grain']['cog_coded_frame']['temporal_offset'], i) = self._read_sint(b, i, 4)

                if i < block_end:
                    (tag, size, i) = self._decode_block_header(b, i, ["unof"], optional=True)

                    if size != 0:
                        meta['grain']['cog_coded_frame']['unit_offsets'] = []
                        (num, i) = self._read_uint(b, i, 2)
                        for u in range(0, num):
                            (offset, i) = self._read_uint(b, i, 4)
                            meta['grain']['cog_coded_frame']['unit_offsets'].append(offset)
            elif tag == "aghd":
                meta['grain']['grain_type'] = "audio"
                meta['grain']['cog_audio'] = {}
                (meta['grain']['cog_audio']['format'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_audio']['channels'], i) = self._read_uint(b, i, 2)
                (meta['grain']['cog_audio']['samples'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_audio']['sample_rate'], i) = self._read_uint(b, i, 4)
            elif tag == "cahd":
                meta['grain']['grain_type'] = "coded_audio"
                meta['grain']['cog_coded_audio'] = {}
                (meta['grain']['cog_coded_audio']['format'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_audio']['channels'], i) = self._read_uint(b, i, 2)
                (meta['grain']['cog_coded_audio']['samples'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_audio']['priming'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_audio']['remainder'], i) = self._read_uint(b, i, 4)
                (meta['grain']['cog_coded_audio']['sample_rate'], i) = self._read_uint(b, i, 4)
            elif tag == "eghd":
                meta['grain']['grain_type'] = "event"
            else:
                raise GSFDecodeError("Unknown type {} at offset {}".format(tag, i), start, length=gbhd_end - start)
        i = block_end
        return (meta, gbhd_end)

    def _decode_grdt(self, b, i):
        (_, size, i) = self._decode_block_header(b, i, ["grdt"])
        if size <= 8:
            return (None, i)
        start = i - 8
        return (b[i:start+size], start + size)

    def _decode_grai(self, b, i):
        start = i
        (tag, size, i) = self._decode_block_header(b, i, ["grai"])
        if tag == "":
            return (None, None, start)
        if size > 0:
            start = i - 8
            end = start + size
            if i <= end - 2:
                (local_id, i) = self._read_uint(b, i, 2)

                if i <= end - 8:
                    (meta, i) = self._decode_gbhd(b, i)
                    data = None
                    if i <= end - 8:
                        (data, i) = self._decode_grdt(b, i)

                    return (self.Grain(meta, data), local_id, start + size)
            return (None, None, end)
        return (None, None, start + 8)

    def decode(self, s):
        """Decode a GSF formatted bytes object, returning a dictionary mapping
        sequence ids to lists of GRAIN objects (or subclasses of such)."""
        if (s):
            self.file_data = BytesIO(s)

        b = None
        i = 0

        (major, minor, i) = self._decode_ssb_header(b, i)
        if (major, minor) != (7, 0):
            raise GSFDecodeBadVersionError("Unknown Version {}.{}".format(major, minor), 0, major, minor)

        (head, i) = self._decode_head(b, i)
        segments = {}

        while i < len(b):
            (grain, local_id, i) = self._decode_grai(b, i)

            if grain is None:
                break

            if local_id not in segments:
                segments[local_id] = []
            segments[local_id].append(grain)

        return (head, segments)


class GSFEncodeError(GSFError):
    """A generic GSF Encoder error, all other GSF Encoder exceptions inherit from it."""
    pass


class GSFEncodeAddToActiveDump(GSFEncodeError):
    """An exception raised when trying to add something to the header of a GSF
    file which has already written its header to the stream."""
    pass


def _write_uint(file, val, size):
    d = bytearray(size)
    for i in range(0, size):
        d[i] = (val & 0xFF)
        val >>= 8
    file.write(d)


def _write_sint(file, val, size):
    if val < 0:
        val = val + (1 << (8*size))
    _write_uint(file, val, size)


def _write_uuid(file, val):
    file.write(val.bytes)


def _write_ts(file, ts):
    _write_uint(file, ts.sec, 6)
    _write_uint(file, ts.ns, 4)


def _write_rational(file, value):
    value = Fraction(value)
    _write_uint(file, value.numerator, 4)
    _write_uint(file, value.denominator, 4)


def seekable(file):  # pragma: no cover
    if PY3:
        return file.seekable()
    else:
        try:
            file.tell()
        except IOError:
            return False
        else:
            return True


class GSFEncoder(object):
    """An encoder for GSF format.

    Constructor takes a single mandatory argument, an io.BytesIO-like object to which the result will be written,
    optional arguments exist for specifying file-level metadata, if no created time is specified the current time
    will be used, if no id is specified one will be generated randomly.

    The main interface are the methods add_grain and dump which add a grain to the file and dump the file to
    the buffer respectively.

    If a streaming format is required then you can instead use the "start_dump" method, followed by adding
    grains as needed, and then the "end_dump" method. Each new grain will be written as it is added. In this mode
    any segments in use MUST be added first before start_dump is called.

    In addition the following properties provide access to file-level metadata:

    major    -- an integer (default 7)
    minor    -- an integer (default 0)
    id       -- a uuid.UUID
    created  -- a datetime.datetime
    tags     -- a tuple of tags
    segments -- a frozendict of GSFEncoderSegments

    The current version of the library is designed for compatibility with v.7.0 of the GSF format. Setting a
    different version number will simply change the reported version number in the file, but will not alter the
    syntax at all. If future versions of this code add support for other versions of GSF then this will change."""
    def __init__(self, file, major=7, minor=0, id=None, created=None, tags=None):
        self.file = file
        self.major = major
        self.minor = minor
        self.id = id
        self.created = created
        self._tags = []

        if self.id is None:
            self.id = uuid1()
        if self.created is None:
            self.created = datetime.now()
        self._segments = {}
        self._next_local = 1
        self._active_dump = False

        if tags is not None:
            for tag in tags:
                try:
                    self.add_tag(tag[0], tag[1])
                except (TypeError, IndexError):
                    raise GSFEncodeError("No idea how to turn {!r} into a tag".format(tag))

    @property
    def tags(self):
        return tuple(self._tags)

    @property
    def segments(self):
        return frozendict(self._segments)

    def add_tag(self, key, value):
        """Add a tag to the file"""
        if self._active_dump:
            raise GSFEncodeAddToActiveDump("Cannot add a new tag to an encoder that is currently dumping")

        self._tags.append(GSFEncoderTag(key, value))

    def add_segment(self, id=None, local_id=None, tags=None):
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
            raise GSFEncodeAddToActiveDump("Cannot add a new segment {} ({!s}) to an encoder that is currently dumping".format(local_id, id))

        seg = GSFEncoderSegment(id, local_id, tags=tags)
        self._segments[local_id] = seg
        return seg

    def add_grain(self, grain, segment_id=None, segment_local_id=None):
        """Add a grain to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        self.add_grains((grain,), segment_id=segment_id, segment_local_id=segment_local_id)

    def add_grains(self, grains, segment_id=None, segment_local_id=None):
        """Add several grains to one of the segments of the file. If no local_segment_id
        is provided then a segment with id equal to segment_id will be used if one
        exists, or the lowest numeric segmemnt if segment_id was not provided.

        If no segment matching the criteria exists then one will be created.
        """
        if segment_local_id is None:
            segments = sorted([local_id for local_id in self._segments if segment_id is None or self._segments[local_id].id == segment_id])
            if len(segments) > 0:
                segment_local_id = segments[0]
        if segment_local_id is not None and segment_local_id in self._segments:
            segment = self._segments[segment_local_id]
        else:
            segment = self.add_segment(id=segment_id, local_id=segment_local_id)
        segment.add_grains(grains)

    def dump(self):
        """Dump the whole contents of this encoder to the file in one go,
        replacing anything that's already there."""

        self.start_dump(all_at_once=True)
        self.end_dump()

    def start_dump(self, all_at_once=False):
        """Start dumping the contents of this encoder to the specified file, if
        the file is seakable then it will replace the current content, otherwise
        it will append."""
        self._active_dump = True

        if seekable(self.file):
            self.file.seek(0)
            self.file.truncate()

        self._write_file_header()
        self._write_head_block(all_at_once=all_at_once)
        self._write_all_grains()

    def end_dump(self, all_at_once=False):
        """End the current dump to the file. In a seakable stream this will write
        all segment counts, in a non-seakable stream it will not."""

        for seg in self._segments.values():
            seg.complete_write()

        if self._active_dump:
            self.file.write(b"grai")
            _write_uint(self.file, 0, 4)
            self._active_dump = False

    def _write_file_header(self):
        self.file.write(b"SSBB")  # signature
        self.file.write(b"grsg")  # file type
        _write_uint(self.file, self.major, 2)
        _write_uint(self.file, self.minor, 2)

    def _write_head_block(self, all_at_once=False):
        size = (31 +
                sum(seg.segm_block_size for seg in self._segments.values()) +
                sum(tag.tag_block_size for tag in self._tags))

        self.file.write(b"head")
        _write_uint(self.file, size, 4)
        _write_uuid(self.file, self.id)
        _write_sint(self.file, self.created.year, 2)
        _write_uint(self.file, self.created.month, 1)
        _write_uint(self.file, self.created.day, 1)
        _write_uint(self.file, self.created.hour, 1)
        _write_uint(self.file, self.created.minute, 1)
        _write_uint(self.file, self.created.second, 1)

        for seg in self._segments.values():
            seg.write_to(self.file, all_at_once=all_at_once)

        for tag in self._tags:
            tag.write_to(self.file)

    def _write_all_grains(self):
        for seg in self._segments.values():
            seg.write_all_grains()


class GSFEncoderTag(object):
    """A class to represent a tag,

    has two properties:

    key
    value

    both strings."""

    def __init__(self, key, value):
        self.key = key
        self.value = value

    @property
    def encoded_key(self):
        return self.key.encode("utf-8")[:65535]

    @property
    def encoded_value(self):
        return self.value.encode("utf-8")[:65535]

    @property
    def tag_block_size(self):
        return 12 + len(self.encoded_key) + len(self.encoded_value)

    def write_to(self, file):
        file.write(b"tag ")
        _write_uint(file, self.tag_block_size, 4)
        _write_uint(file, len(self.encoded_key), 2)
        file.write(self.encoded_key)
        _write_uint(file, len(self.encoded_value), 2)
        file.write(self.encoded_value)

    def __eq__(self, other):
        return other.__eq__((self.key, self.value))


class GSFEncoderSegment(object):
    """A class to represent a segment within a GSF file, used for constructing them."""

    def __init__(self, id, local_id, tags=None):
        self.id = id
        self.local_id = local_id
        self._count_pos = -1
        self._file = None
        self._tags = []
        self._grains = []

        if tags is not None:
            for tag in tags:
                try:
                    self.add_tag(tag[0], tag[1])
                except (TypeError, IndexError):
                    raise GSFEncodeError("No idea how to turn {!r} into a tag".format(tag))

    @property
    def count(self):
        return len(self.grains)

    @property
    def segm_block_size(self):
        return 34 + sum(tag.tag_block_size for tag in self._tags)

    @property
    def tags(self):
        return tuple(self._tags)

    @property
    def grains(self):
        return tuple(self._grains)

    def write_to(self, file, all_at_once=False):
        self._file = file
        file.write(b"segm")
        _write_uint(file, self.segm_block_size, 4)

        _write_uint(file, self.local_id, 2)
        _write_uuid(file, self.id)
        if all_at_once:
            _write_sint(file, self.count, 8)
        else:
            if seekable(file):
                self._count_pos = file.tell()
            _write_sint(file, -1, 8)

        for tag in self._tags:
            tag.write_to(file)

    def write_all_grains(self):
        for grain in self._grains:
            self._write_grain(grain)

    def _write_grain(self, grain):
        gbhd_size = self._gbhd_size_for_grain(grain)

        self._file.write(b"grai")
        _write_uint(self._file, 10 + gbhd_size + 8 + grain.length, 4)

        _write_uint(self._file, self.local_id, 2)

        self._file.write(b"gbhd")
        _write_uint(self._file, gbhd_size, 4)

        _write_uuid(self._file, grain.source_id)
        _write_uuid(self._file, grain.flow_id)
        self._file.write(b"\x00"*16)
        _write_ts(self._file, grain.origin_timestamp)
        _write_ts(self._file, grain.sync_timestamp)
        _write_rational(self._file, grain.rate)
        _write_rational(self._file, grain.duration)

        if len(grain.timelabels) > 0:
            self._file.write(b"tils")
            _write_uint(self._file, 10 + 29*len(grain.timelabels), 4)

            _write_uint(self._file, len(grain.timelabels), 2)

            for label in grain.timelabels:
                tag = (label['tag'].encode('utf-8') + (b"\x00" * 16))[:16]
                self._file.write(tag)
                _write_uint(self._file, label['timelabel']['frames_since_midnight'], 4)
                _write_uint(self._file, label['timelabel']['frame_rate_numerator'], 4)
                _write_uint(self._file, label['timelabel']['frame_rate_denominator'], 4)
                _write_uint(self._file, 1 if label['timelabel']['drop_frame'] else 0, 1)

        if grain.grain_type == "video":
            self._write_vghd_for_grain(grain)
        elif grain.grain_type == "coded_video":
            self._write_cghd_for_grain(grain)
        elif grain.grain_type == "audio":
            self._write_aghd_for_grain(grain)
        elif grain.grain_type == "coded_audio":
            self._write_cahd_for_grain(grain)
        elif grain.grain_type == "event":
            self._write_eghd_for_grain(grain)
        elif grain.grain_type != "empty":  # pragma: no cover (should be unreachable)
            raise GSFEncodeError("Unknown grain type: {}".format(grain.grain_type))

        self._file.write(b"grdt")
        _write_uint(self._file, 8 + grain.length, 4)

        if grain.data is not None:
            self._file.write(grain.data)

    def _gbhd_size_for_grain(self, grain):
        size = 92
        if len(grain.timelabels) > 0:
            size += 10 + 29*len(grain.timelabels)
        if grain.grain_type == "video":
            size += self._vghd_size_for_grain(grain)
        elif grain.grain_type == "coded_video":
            size += self._cghd_size_for_grain(grain)
        elif grain.grain_type == "audio":
            size += self._aghd_size_for_grain(grain)
        elif grain.grain_type == "coded_audio":
            size += self._cahd_size_for_grain(grain)
        elif grain.grain_type == "event":
            size += self._eghd_size_for_grain(grain)
        elif grain.grain_type != "empty":
            raise GSFEncodeError("Unknown grain type: {}".format(grain.grain_type))
        return size

    def _vghd_size_for_grain(self, grain):
        size = 44
        if len(grain.components) > 0:
            size += 10 + 16*len(grain.components)
        return size

    def _write_vghd_for_grain(self, grain):
        self._file.write(b"vghd")
        _write_uint(self._file, self._vghd_size_for_grain(grain), 4)

        _write_uint(self._file, int(grain.format), 4)
        _write_uint(self._file, int(grain.layout), 4)
        _write_uint(self._file, int(grain.width), 4)
        _write_uint(self._file, int(grain.height), 4)
        _write_uint(self._file, int(grain.extension), 4)
        if grain.source_aspect_ratio is None:
            _write_rational(self._file, Fraction(0, 1))
        else:
            _write_rational(self._file, grain.source_aspect_ratio)
        if grain.pixel_aspect_ratio is None:
            _write_rational(self._file, Fraction(0, 1))
        else:
            _write_rational(self._file, grain.pixel_aspect_ratio)

        if len(grain.components) > 0:
            self._file.write(b"comp")
            _write_uint(self._file, 10 + 16*len(grain.components), 4)

            _write_uint(self._file, len(grain.components), 2)

            for comp in grain.components:
                _write_uint(self._file, comp.width, 4)
                _write_uint(self._file, comp.height, 4)
                _write_uint(self._file, comp.stride, 4)
                _write_uint(self._file, comp.length, 4)

    def _eghd_size_for_grain(self, grain):
        return 9

    def _write_eghd_for_grain(self, grain):
        self._file.write(b"eghd")
        _write_uint(self._file, self._eghd_size_for_grain(grain), 4)

        _write_uint(self._file, 0x00, 1)

    def _aghd_size_for_grain(self, grain):
        return 22

    def _write_aghd_for_grain(self, grain):
        self._file.write(b"aghd")
        _write_uint(self._file, self._aghd_size_for_grain(grain), 4)

        _write_uint(self._file, int(grain.format), 4)
        _write_uint(self._file, int(grain.channels), 2)
        _write_uint(self._file, int(grain.samples), 4)
        _write_uint(self._file, int(grain.sample_rate), 4)

    def _cghd_size_for_grain(self, grain):
        size = 37
        if len(grain.unit_offsets) > 0:
            size += 10 + 4*len(grain.unit_offsets)
        return size

    def _write_cghd_for_grain(self, grain):
        self._file.write(b"cghd")
        _write_uint(self._file, self._cghd_size_for_grain(grain), 4)

        _write_uint(self._file, int(grain.format), 4)
        _write_uint(self._file, int(grain.layout), 4)
        _write_uint(self._file, int(grain.origin_width), 4)
        _write_uint(self._file, int(grain.origin_height), 4)
        _write_uint(self._file, int(grain.coded_width), 4)
        _write_uint(self._file, int(grain.coded_height), 4)
        _write_uint(self._file, 1 if grain.is_key_frame else 0, 1)
        _write_uint(self._file, int(grain.temporal_offset), 4)

        if len(grain.unit_offsets) > 0:
            self._file.write(b"unof")
            _write_uint(self._file, 10 + 4*len(grain.unit_offsets), 4)

            _write_uint(self._file, len(grain.unit_offsets), 2)

            for i in range(0, len(grain.unit_offsets)):
                _write_uint(self._file, grain.unit_offsets[i], 4)

    def _cahd_size_for_grain(self, grain):
        return 30

    def _write_cahd_for_grain(self, grain):
        self._file.write(b"cahd")
        _write_uint(self._file, self._cahd_size_for_grain(grain), 4)

        _write_uint(self._file, int(grain.format), 4)
        _write_uint(self._file, int(grain.channels), 2)
        _write_uint(self._file, int(grain.samples), 4)
        _write_uint(self._file, int(grain.priming), 4)
        _write_uint(self._file, int(grain.remainder), 4)
        _write_uint(self._file, int(grain.sample_rate), 4)

    def complete_write(self):
        if self._file is None:
            return

        if seekable(self._file) and self._count_pos != -1:
            curpos = self._file.tell()
            self._file.seek(self._count_pos)
            _write_sint(self._file, self.count, 8)
            self._file.seek(curpos)

        self._file = None
        self._count_pos = -1

    def add_tag(self, key, value):
        """Add a tag to the segment"""
        if self._file is not None:
            raise GSFEncodeAddToActiveDump("Cannot add a tag to a segment which is part of an active export")
        self._tags.append(GSFEncoderTag(key, value))

    def add_grain(self, grain):
        """Add a grain to the segment, which should be a Grain object"""
        self._grains.append(grain)
        if self._file is not None:
            self._write_grain(grain)

    def add_grains(self, grains):
        """Add several grains to the segment, the parameter should be an
        iterable of grain objects"""
        for grain in grains:
            self.add_grain(grain)
