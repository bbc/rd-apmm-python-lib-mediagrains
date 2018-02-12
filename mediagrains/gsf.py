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

from __future__ import print_function, absolute_import
from . import Grain
from six import indexbytes
from uuid import UUID
from datetime import datetime
from nmoscommon.timestamp import Timestamp
from fractions import Fraction

__all__ = ["GSFDecoder", "loads", "GSFError", "GSFDecodeError",
           "GSFDecodeBadFileTypeError", "GSFDecodeBadVersionError"]

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


class GSFError(Exception):
    pass


class GSFDecodeError(GSFError):
    def __init__(self, msg, i, length=None):
        super(GSFDecodeError, self).__init__(msg)
        self.offset = i
        self.length = length


class GSFDecodeBadFileTypeError(GSFDecodeError):
    def __init__(self, msg, i, filetype):
        super(GSFDecodeBadFileTypeError, self).__init__(msg, i, 8)
        self.filetype = filetype


class GSFDecodeBadVersionError(GSFDecodeError):
    def __init__(self, msg, i, major, minor):
        super(GSFDecodeBadVersionError, self).__init__(msg, i, 8)
        self.major = major
        self.minor = minor


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
            r -= (1 << (8*i))
        return (r, i)

    def _read_string(self, b, i, l):
        return (b[i:i+l].decode(encoding='ascii'), i+l)

    def _read_varstring(self, b, i):
        (l, i) = self._read_uint(b, i, 2)
        return (self._read_string(b, i, l), i+l)

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
        while i < len(b):
            (tag, i) = self._read_string(b, i, 4)
            (size, i) = self._read_uint(b, i, 4)
            if allowed is not None and tag not in allowed:
                if optional:
                    return ("", 0, start)
                else:
                    continue
            else:
                return (tag, size, i)
        return ("", 0, start)

    def _decode_head(self, b, i):
        start = i
        head = {}

        (tag, size, i) = self._decode_block_header(b, i, ["head"])
        (head['id'], i) = self._read_uuid(b, i)
        (head['created'], i) = self._read_timestamp(b, i)
        head['segments'] = []
        head['tags'] = []

        head_end = start + size
        while i < head_end:
            segm_start = i
            (tag, size, i) = self._decode_block_header(b, i, ["segm", "tag "])
            segm_end = segm_start + size
            if tag == "tag ":
                (tag, s, i) = self._decode_block_header(b, i, ["tag "])
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
                    (key, i) = self._read_varstring(b, i)
                    (val, i) = self._read_varstring(b, i)
                    segm.tags.append((key, val))
                head['segments'].append(segm)

            if i > segm_end:
                raise GSFDecodeError("Size of segm block not large enough to contain its contents", segm_start, length=segm_end - segm_start)

        if i != head_end:
            raise GSFDecodeError("Size of head block not large enough to contain its contents", start, length=head_end - start)

        return (head, i)

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
            (meta['grain']['timelabels'], i) = self._decode_tils(b, block_start)

        block_start = i
        (tag, size, i) = self._decode_block_header(b, i, ["tils", "vghd", "cghd", "aghd", "cahd", "eghd"])
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
            meta['grain']['cog_frame']['source_aspect_ratio'] = {'numerator': ar.numerator,
                                                                 'denominator': ar.denominator}
            (ar, i) = self._read_rational(b, i)
            meta['grain']['cog_frame']['pixel_aspect_ratio'] = {'numerator': ar.numerator,
                                                                'denominator': ar.denominator}
            meta['grain']['cog_frame']['components'] = []
            if i < block_end:
                comp_start = i
                (tag, size, i) = self._decode_block_header(b, i, ["comp"], optional=True)
                comp_end = comp_start + size
                if size != 0:
                    (n_comps, i) = self._read_uint(b, i, 2)
                    for c in range(0, n_comps):
                        comp = {}
                        (comp['width'], i) = self._read_uint(b, i, 4)
                        (comp['height'], i) = self._read_uint(b, i, 4)
                        (comp['stride'], i) = self._read_uint(b, i, 4)
                        (comp['length'], i) = self._read_uint(b, i, 4)
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
            (meta['grain']['cog_coded_frame']['key_frame'], i) = self._read_bool(b, i)
            (meta['grain']['cog_coded_frame']['temporal_offset'], i) = self._read_sint(b, i, 4)

            if i < block_end:
                unof_start = i
                (tag, size, i) = self._decode_block_header(b, i, ["unof"], optional=True)
                unof_end = unof_start + size

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
        start = i
        (_, size, i) = self._decode_block_header(b, i, ["grdt"])
        return (b[i:start+size], start + size)

    def _decode_grai(self, b, i):
        (_, size, i) = self._decode_block_header(b, i, ["grai"])
        if size > 0:
            (local_id, i) = self._read_uint(b, i, 2)

            (meta, i) = self._decode_gbhd(b, i)
            (data, i) = self._decode_grdt(b, i)

            return (self.Grain(meta, data), local_id, i)
        else:
            return (None, None, i)

    def decode(self, s):
        """Decode a GSF formatted bytes object, returning a dictionary mapping
        sequence ids to lists of GRAIN objects (or subclasses of such)."""
        b = bytes(s)
        i = 0

        (major, minor, i) = self._decode_ssb_header(b, i)
        if (major, minor) != (7,0):
            raise GSFDecodeBadVersionError("Unknown Version {}.{}".format(major, minor), 0, major, minor)

        (head, i) = self._decode_head(b,i)
        segments = {}

        while i < len(b):
            (grain, local_id, i) = self._decode_grai(b,i)

            if grain is None:
                break

            if local_id not in segments:
                segments[local_id] = []
            segments[local_id].append(grain)

        return (head, segments)

if __name__ == "__main__":  # pragma: no cover
    import sys
    fname = sys.argv[1]
    f = open(fname, "rb")
    b = f.read()

    print(loads(b))
