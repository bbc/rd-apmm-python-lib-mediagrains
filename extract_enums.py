#!/usr/bin/python

from __future__ import print_function
import sys
import re
from cffi import FFI

fname = sys.argv[1]
f = open(fname, 'r')
cdata = '\n'.join( line for line in f.read().split('\n') if len(line) == 0 or line[0] != '#' )

ffi = FFI()

enums = [("CogFrameFormat", "COG_FRAME_FORMAT_"),
         ("CogFrameLayout", "COG_FRAME_LAYOUT_"),
         ("CogAudioFormat", "COG_AUDIO_FORMAT_"),]

for (name, prefix) in enums:
    definition = re.search(r"typedef\s+enum\s+_" + name + r"\s*{\s*[^}]*}\s*" + name + r"\s*;".format('CogFrameFormat','CogFrameFormat'), cdata, re.M).group(0)
    ffi.cdef(definition)

c = ffi.dlopen('c')


if len(sys.argv) > 2:
    outfile = open(sys.argv[2], 'w')
else:
    outfile = sys.stdout
    
print("from enum import IntEnum", file=outfile)
print(file=outfile)
print("__all__ = " + repr([ name for (name,prefix) in enums ]), file=outfile)
for (name, prefix) in enums:
    print(file=outfile)
    print(file=outfile)
    print("class {}(IntEnum):".format(name), file=outfile)
    data = sorted([ (name[len(prefix):], getattr(c,name)) for name in dir(c) if name.startswith(prefix) ], key=lambda x:x[1])
    print('\n'.join("    {!s}={!s}".format(name, hex(key)) for (name, key) in data), file=outfile)
