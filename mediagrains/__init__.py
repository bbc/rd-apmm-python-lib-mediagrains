#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

"""\
Library for handling media grains in pure python.

The library contains the functions: Grain, VideoGrain, CodedVideoGrain,
AudioGrain, CodedAudioGrain, and EventGrain as well as the module gsf.

The individual functions document their useage.

The classes returned from the functions are fully useable as if they were a
tuple:

(meta, data)

where "meta" is a dictionary containing grain metadata in a standard format,
and "data" is a bytes-like object. When the various constructor functions
are used in a way that constructs a new data element they will construct a
bytearray object of the apropriate size. Remember that in Python 2 bytes-like
objects are stringlike, but in Python 3 they resemble sequences of integers.

Notably this means that the data element of these grains is fully compatible
with numpy and similar libraries.

The gsf and grain submodules have their own documentation.
"""

from __future__ import absolute_import
from .grain_constructors import Grain, VideoGrain, CodedVideoGrain, AudioGrain, CodedAudioGrain, EventGrain

__all__ = ["Grain", "VideoGrain", "CodedVideoGrain", "AudioGrain", "CodedAudioGrain", "EventGrain"]
