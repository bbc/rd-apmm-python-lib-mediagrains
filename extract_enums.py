#!/usr/bin/python

import sys
from cffi import FFI

fname = sys.argv[1]
f = open(fname, 'r')
cdata = f.read()

ffi = FFI()
ffi.cdef(cdata)

c = ffi.dlopen('c')

enums = [("CogFrameFormat", "COG_FRAME_FORMAT_"),
         ("CogFrameLayout", "COG_FRAME_LAYOUT_")]

print "from enum import IntEnum"
print
print "__all__ = " + repr([ name for (name,prefix) in enums ])
for (name, prefix) in enums:
    print
    print
    print "class {}(IntEnum):".format(name)
    data = sorted([ (name[len(prefix):], getattr(c,name)) for name in dir(c) if name.startswith(prefix) ], key=lambda x:x[1])
    print '\n'.join("    {!s}={!s}".format(name, hex(key)) for (name, key) in data)
