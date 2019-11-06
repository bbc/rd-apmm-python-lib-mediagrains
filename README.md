# mediagrains

A python library for handling grain-based media in a python-native
style.

## Introduction

Provides constructor functions for various types of grains and classes
that nicely wrap those grains, as well as a full serialisation and
deserialisation library for GSF format. Please read the pydoc
documentation for more details.

Some useful tools for handling the Grain Sequence Format (GSF) file format
are also included - see [Tools](#tools).

## Installation

### Requirements

* A working Python 3.6+ installation
* BBC R&D's internal deb repository set up as a source for apt (if installing via apt-get)
* The tool [tox](https://tox.readthedocs.io/en/latest/) is needed to run the unittests, but not required to use the library.

### Steps

```bash
# Install from pip
$ pip install mediagrains

# Install via apt-get
$ apt-get install python3-mediagrains

# Install directly from source repo
$ git clone git@github.com:bbc/rd-apmm-python-lib-mediagrains.git
$ cd rd-apmm-python-lib-mediagrains
$ pip install -e .
```

## Usage

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

(a more natural interface for accessing data exists in the form of numpy arrays. See later.)

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

If the underlying file is seekable then the end_dump call will upade all segment
metadata to list the correct grain count, otherwise the counts will be
left at -1.

In addition the library contains a relatively rich grain comparison
mechanism in the submodule `comparison`. An example of useage is as
follows:

```python
>>> from mediagrains.comparison import compare_grain
>>> from mediagrains.testsignalgenerator import LumaSteps
>>> from uuid import uuid1
>>> from mediatimestamp import Timestamp
>>> src_id = uuid1()
>>> flow_id = uuid1()
>>> ots = Timestamp()
>>> gen = LumaSteps(src_id, flow_id, 1920, 1080, origin_timestamp=ots)
>>> a = next(gen)
>>> b = next(gen)
>>> print(compare_grain(a, b))
❌   Grains do not match
  ✅   <a/b>.height == 1080
  ✅   Binary data <a/b>.data are equal
  ✅   <a/b>.format == <CogFrameFormat.U8_444: 8192>
  ✅   <a/b>.length == 6220800
  ❌   a.origin_timestamp - b.origin_timestamp == -0:40000000, not the expected 0:0
  ❌   a.sync_timestamp - b.sync_timestamp == -0:40000000, not the expected 0:0
  ✅   <a/b>.flow_id == UUID('7ff37130-d904-11e8-9fa5-5065f34ed007')
  ✅   <a/b>.grain_type == 'video'
  ✅   Lists match
    ✅   len(<a/b>.timelabels) == 0
  ✅   <a/b>.layout == <CogFrameLayout.FULL_FRAME: 0>
  ✅   <a/b>.width == 1920
  ✅   <a/b>.source_id == UUID('7bf845f6-d904-11e8-9fa5-5065f34ed007')
  ✅   <a/b>.rate == Fraction(25, 1)
  ✅   a.creation_timestamp - b.creation_timestamp == 0:0 as expected
  ✅   <a/b>.duration == Fraction(1, 25)
```

This output gives a relatively detailed breakdown of the differences
between two grains, both as a printed string (as seen above) and also
in a data-centric fashion as a tree structure which can be
interrogated in code.

### Numpy arrays

An additional feature is provided in the form of numpy array access to the data in a grain. As such the above example of creating colourbars can be done more easily:

```Python console
>>> from mediagrains.numpy import VideoGrain
>>> from uuid import uuid1
>>> from mediagrains.cogenums import CogFrameFormat, CogFrameLayout
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
>>> for c in range(0, 3):
...     for x in range(0, grain.components[c].width):
...         for y in range(0, grain.components[c].height):
...             grain.component_data[c][x, y] = colours[x*len(colours)//grain.components[c].width][c]
```

## Documentation

The API is well documented in the docstrings of the module mediagrains, to view:

```bash
pydoc mediagrains
```

## Tools
Some tools are installed with the library to make working with the Grain Sequence Format (GSF) file format easier.

* `wrap_video_in_gsf` - Provides a means to read raw video essence and generate a GSF file.
* `wrap_audio_in_gsf` - As above, but for audio.
* `extract_from_gsf` - Read a GSF file and dump out the raw essence within.
* `gsf_probe` - Read metadata about the segments in a GSF file.

For example, to generate a GSF file containing a test pattern from `ffmpeg`, dump the metadata and then play it out
again:
```bash
ffmpeg -f lavfi -i testsrc=duration=20:size=1920x1080:rate=25 -pix_fmt yuv422p10le -c:v rawvideo -f rawvideo - | \
wrap_video_in_gsf - output.gsf --size 1920x1080 --format S16_422_10BIT --rate 25
gsf_probe output.gsf
extract_gsf_essence output.gsf - | ffplay -f rawvideo -pixel_format yuv422p10 -video_size 1920x1080 -framerate 25 pipe:0
```

To do the same with a sine wave:
```bash
ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" -f s16le -ac 2 - | wrap_audio_in_gsf - output_audio.gsf --sample-rate 44100
gsf_probe output_audio.gsf
extract_gsf_essence output_audio.gsf - | ffplay -f s16le -ac 2 -ar 44100 pipe:0
```

## Development
### Testing

To run the unittests for this package in a virtual environment follow these steps:

```bash
$ git clone git@github.com:bbc/rd-apmm-python-lib-mediagrains.git
$ cd rd-apmm-python-lib-mediagrains
$ make test
```
### Packaging

Debian and RPM packages can be built using:

```bash
# Debian packaging
$ make deb

# RPM packageing
$ make rpm
```

### Continuous Integration

This repository includes a Jenkinsfile which makes use of custom steps defined in a BBC internal
library for use on our own Jenkins instances. As such it will not be immediately useable outside
of a BBC environment, but may still serve as inspiration and an example of how to implement CI
for this package.

## Versioning

We use [Semantic Versioning](https://semver.org/) for this repository

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## Contributing

All contributions are welcome, before submitting you must read and sign a copy of the [Individual Contributor License Agreement](ICLA.md)

Please ensure you have run the test suite before submitting a Pull Request, and include a version bump in line with our [Versioning](#versioning) policy.

## Authors

* James Weaver (james.barrett@bbc.co.uk)
* Philip deNier (philip.denier@bbc.co.uk)
* Sam Mesterton-Gibbons (sam.mesterton-gibbons@bbc.co.uk)
* Alex Rawcliffe (alex.rawcliffe@bbc.co.uk)

## License

See [LICENSE.md](LICENSE.md)
