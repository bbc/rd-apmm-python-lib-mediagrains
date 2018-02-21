# rd-apmm-python-lib-mediagrains

A python library for handling grain-based media in a python-native
style. Please read the poydoc documentation for more details.

Provides constructor functions for various types of grains and classes
that nicely wrap those grains, as well as a full serialisation and
deserialisation library for GSF format.

## Installing with Python and make

To run the installer run

> make install

to create a redistributable source tarball call

> make source

## Running tests

To run the tests for python2 run

> make test2

to run the tests for python3 run

> make test3

to run both run

> make test

All tests are run inside a virtual environment so as to avoid
polluting the global python environment.

## prerequisites

The nmoscommon library used to provide the Timestamp class is
needed during testing. This library is available here:

< git+https://github.com/jamesba/nmos-common/@python3 >

to install this package that one must be installed, to run the tests
it must be available in a repository that pip will look at during
package instalation (if you don't have such a repo you can set one up
quickly using devpi).

## Examples

As an example of using this in your own code the following is a simple
program to load the contents of a GSF file and print the timestamp of
each grain.

```Python console
>>> from mediagrains.gsf import load
>>> f = open('examples/video.gsf', "rb")
>>> (head, segments) = load(f)
>>> print('\n'.join(str(grain.origin_timestamp) for grain in segments[1]))
1420102800:0
1420102800:20000000
1420102800:40000000
1420102800:60000000
1420102800:80000000
1420102800:100000000
1420102800:120000000
1420102800:140000000
1420102800:160000000
1420102800:180000000
```

Alternatively to create a new video grain in 10-bit planar YUV 4:2:0 and fill
it with colour-bars:

```Python console
>>> from mediagrains import VideoGrain
>>> from uuid import uuid1
>>> from mediagrains.cogenum import CogFrameFormat, CogFrameLayout
>>> src_id = uuid1()
>>> flow_id = uuid1()
>>> grain = VideoGrain(src_id, flow_id, cog_frame_format=CogFrameFormat.S16_422_10BIT, width=1920, height=1080)
>>> colours = [
...      (0x3FF, 0x000, 0x3FF),
...      (0x3FF, 0x3FF, 0x000),
...      (0x3FF, 0x000, 0x000),
...      (0x3FF, 0x3FF, 0x3FF),
...      (0x3FF, 0x200, 0x3FF),
...      (0x3FF, 0x3FF, 0x200) ]
>>> x_offset = [0, 0, 0]
>>> for colour in colours:
...     i = 0
...     for c in grain.components:
...             for x in range(0,c.width//len(colours)):
...                     for y in range(0,c.height):
...                             grain.data[c.offset + y*c.stride + (x_offset[i] + x)*2 + 0] = colour[i] & 0xFF
...                             grain.data[c.offset + y*c.stride + (x_offset[i] + x)*2 + 1] = colour[i] >> 8
...             x_offset[i] += c.width//len(colours)
...             i += 1
```

The object grain can then be freely used for whatever video processing
is desired, or it can be serialised into a GSF file as follows:

```Python console
>>> from mediagrains.gsf import dump
>>> f = open('dummyfile.gsf', 'wb')
>>> dump(f, [grain])
>>> f.close()
```
The encoding module also supports a "progressive" mode where an
encoder object is created and a dump started, then grains can be added
and will be written to the output file as they are added.

```Python console
>>> from uuid import uuid1
>>> from mediagrains import Grain
>>> from mediagrains.gsf import GSFEncoder
>>> src_id = uuid1()
>>> flow_id = uuid1()
>>> f = open('dummyfile.gsf', 'wb')
>>> enc = GSFEncoder(f)
>>> seg = enc.add_segment()  # This must be done before the call to start_dump
>>> enc.start_dump()  # This writes the file header and starts the export
>>> seg.add_grain(Grain(src_id, flow_id))  # Adds a grain and writes it to the file
>>> seg.add_grain(Grain(src_id, flow_id))  # Adds a grain and writes it to the file
>>> seg.add_grain(Grain(src_id, flow_id))  # Adds a grain and writes it to the file
>>> enc.end_dump()  # This ends the export and finishes off the file
>>> f.close()
```

If the underlying file is seakable then the end_dump call will upade all segment
metadata to list the correct grain count, otherwise the counts will be left at -1.
