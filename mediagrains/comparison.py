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
The submodule which gives comparison capabilities.

Contains a fairly complex set of methods for comparing grains in ways that
are more nuanced than the simple equality comparison provided by the grain class
itself.

The main interface is via the compare_grain function.

Options can be passed to comparisons which are constructed using the objects Exclude and ExpectedDifference.
These two objects provide a convenient (and similar) interface. By accessing attributes of these objects that have
the same names as attributes of the objects to be compared you can identify which attributes to refer to.

eg.

Exclude.creation_timestamp

is an option that causes the comparison operation to ignore any differences in the creation_timestamp member of the compared
objects.

For ExpectedDifference there is an additional step, which is to apply comparison operations, so:

(ExpectedDifference.creation_timestamp > TimeOffset(0, 64))

is an option that requires (a.creation_timestamp - b.creation_timestamp) to be greater than 64 nanoseconds.

This mechanism may be expanded for further option types in the future.
"""

from __future__ import print_function
from __future__ import absolute_import

from fractions import Fraction
from mediatimestamp import TimeOffset
from difflib import SequenceMatcher

from six.moves import reduce
import struct
import sys

from .cogenums import CogAudioFormat, CogFrameFormat, COG_FRAME_IS_PACKED, COG_FRAME_IS_COMPRESSED, COG_FRAME_FORMAT_BYTES_PER_VALUE

__all__ = ["compare_grain", "Exclude", "ExpectedDifference"]


#
# The compare_grain method is the main actual interface for this module
#
def compare_grain(a, b, *options):
    """
    Compare two grains.

    :param a: the first grain
    :param b: the second grain
    :param *options: Additional arguments are options to pass to this comparison. Currently only two types of options are supported:
    Exclude.<attribute name> causes the named attribute to be excluded from the comparison. Whereas for integer and timestamp attributes
    it is also possible to use a second type of option: ExpectedDifference.<attribute_name> == <value> (or >=, <, <=, >, !=) will set a criteria
    for succesful comparison on that attribute that is less strict that the standard requirement that the values be equal to each other.

    Eg.

    compare(a, b, Exclude.data, ExpectedDifference.sync_timestamp >= TimeOffset(64, 0))

    will compare the grains, ignoring differences in their data payloads, but requiring that instead of being equal the difference between their sync_timestamps
    must be greater than or equal to 64 seconds.

    :return: an object which is truthy if the comparison matched and falsy if it didn't, in addition the object has a detailed
    human readable summary of the differences between the grains obrainable by calling str on it. In addition any access to an
    attribute of this object that is possessed by grains (eg. .creation_timestamp, .data, .length) will provide another object
    that behaves similarly but represents only that attribute and any attributes/entries it contains. Each such object at any level
    in the tree can be tested as a boolean and can also have .excluded() called on it, which will return True iff the original comparison
    excluded that attribute.
    """
    return GrainComparisonResult(a, b, options=options)


#
# Primarily as syntactic sugar the Exclude and ExpectedDifference objects
# are exported to make it easier to construct ComparisonOptions in a simple fashion
#
class _Exclude(object):
    def __getattr__(self, attr):
        return ComparisonExclude("{}." + attr)


class _ExpectedDifference(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return self.path.format("ExpectedDifference")

    def __eq__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x == other, "{} == {!r}".format(self.path.format('ExpectedDifference'), other))

    def __ne__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x != other, "{} != {!r}".format('ExpectedDifference', other))

    def __lt__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x < other, "{} < {!r}".format('ExpectedDifference', other))

    def __le__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x <= other, "{} <= {!r}".format('ExpectedDifference', other))

    def __gt__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x > other, "{} > {!r}".format('ExpectedDifference', other))

    def __ge__(self, other):
        return ComparisonExpectDifferenceMatches(self.path, lambda x: x >= other, "{} >= {!r}".format('ExpectedDifference', other))

    def __and__(self, other):
        if not isinstance(other, ComparisonExpectDifferenceMatches):
            raise ValueError("{!r} & {!r} is not a valid operation".format(self, other))
        elif other.path != self.path:
            raise ValueError("{!r} & {!r} is not a valid operation: When combining ExpectedDifference operations with & they must refer to the same attribute".format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(self.path, lambda x: self.matcher(x) and other.matcher(x), "{!r} & {!r}".format(self, other))

    def __or__(self, other):
        if not isinstance(other, ComparisonExpectDifferenceMatches):
            raise ValueError("{!r} | {!r} is not a valid operation".format(self, other))
        elif other.path != self.path:
            raise ValueError("{!r} | {!r} is not a valid operation: When combining ExpectedDifference operations with | they must refer to the same attribute".format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(self.path, lambda x: self.matcher(x) or other.matcher(x), "{!r} | {!r}".format(self, other))

    def __getattr__(self, attr):
        return _ExpectedDifference(self.path + "." + attr)


Exclude = _Exclude()


ExpectedDifference = _ExpectedDifference("{}")


#
# EVERYTHING BELOW THIS POINT IS AN INTERNAL IMPLEMENTATION DETAIL AND NOT EXPECTED TO BE USED DIRECTLY
#

#
# The ComparisonResult class and its desscendents implement most of the actual comparison logic
#
class ComparisonResult (object):
    """
    Abstract base class for comparison results.

    public interface, attributes, all read only:

    identifier -- an identifier identifing what was being compared, will contain a single {} for substituting the name of the top level object
    attr -- an attribute name which identifies this within it's immedaite parent. Sometimes is None
    a -- the first object that was compared
    b -- the second object that was compared
    children -- a list of ComparisonResult objects for sub-comparisons
    msg -- a human readable message to explain this result

    subclasses should set _identifier and also implement compare.

    in addition the object itself is truthy if the comparison of a and b match,
    and falsy if they do not.
    """
    def __init__(self, identifier, a, b, options=[], attr=None, key=None):
        self._a = a
        self._b = b
        self._identifier = identifier
        self._options = list(options)
        self._attr = attr
        self._key = key
        (self._equal, self._msg, self._children) = self.compare(a, b)

    def __bool__(self):
        return self._equal

    __nonzero__ = __bool__

    @property
    def attr(self):
        return self._attr

    @property
    def key(self):
        return self._key

    @property
    def identifier(self):
        return self._identifier

    @property
    def a(self):
        return self._a

    @property
    def b(self):
        return self._b

    @property
    def children(self):
        return self._children

    @property
    def msg(self):
        msgs = []
        msgs += ['(' + c.msg + ')' for c in self._children if not c and not c.excluded()]
        msgs += ['<IGNORING: ' + c.msg + '>' for c in self._children if not c and c.excluded()]
        if len(msgs) == 0:
            return self._msg
        else:
            return self._msg + ': ' + '; '.join(msgs)

    def excluded(self):
        return (len([option for option in self._options if isinstance(option, ComparisonExclude) and self._identifier == option.path]) != 0)

    def ownoptions(self):
        return [option for option in self._options if self._identifier == option.path]

    def compare(self, a, b):
        """Override in subclasses to return a tripple:
        (equal, msg, children)

        where:
          equal    - is True if a and b match and False otherwise
          msg      - is a human readable string explaining the matching
          children - is a list of comparison objects if this comparison was made
                     by combining other ones.
        """
        return (False, "A generic comparison always fails", [])

    def failing_attributes(self):
        """Call to determine which attributes of the compared objects failed to match

        :returns: a list of strings, which are attribute names in the compared objects
        """
        return [c.attr for c in self.children if not c and c.attr is not None]

    def failing_keys(self):
        """Call to determine which keys of the compared containers failed to match

        :returns: a list of strings, which are keys names in the compared containers
        """
        return [c.key for c in self.children if not c and c.key is not None]

    def _str(self, prefix=""):
        r = prefix
        if self.excluded():
            r += '\u25EF   '
        elif self.__bool__():
            r += '\u2705   '
        else:
            r += '\u274c   '
        r += self._msg
        if len(self._children) == 0:
            return r
        r += '\n'
        prefix = prefix + "  "
        r += '\n'.join(c._str(prefix=prefix) for c in self._children)
        return r

    def __str__(self):
        return self._str()

    def __repr__(self):
        return "{}(identifier={!r}, a={!r}, b={!r}, options={!r})".format(self.__class__.__name__, self._identifier, self._a, self._b, self._options)

    def subcomparison_for_attribute(self, key):
        results = [c for c in self.children if c.attr == key]
        if len(results) == 0:
            raise KeyError("Key {!r} is not known in {!r}".format(key, self))
        else:
            return results[0]

    def __getattr__(self, key):
        try:
            return self.subcomparison_for_attribute(key)
        except KeyError:
            raise AttributeError

    def subcomparison_for_key(self, key):
        results = [c for c in self.children if c.key == key]
        if len(results) == 0:
            raise KeyError
        else:
            return results[0]

    def __getitem__(self, key):
        return self.subcomparison_for_key(key)


class EqualityComparisonResult(ComparisonResult):
    def compare(self, a, b):
        if a == b:
            return (True, "{} == {!r}".format(self._identifier.format('<a/b>'), a), [])
        else:
            return (False, "{} == {!r}, {} == {!r} no match".format(self._identifier.format('a'), a, self._identifier.format('b'), b), [])


class DataEqualityComparisonResult(ComparisonResult):
    """This comparison result is used for comparing long data strings to each other, and provides useful information like the first byte at which they differ"""
    def __init__(self, identifier, a, b, words_per_sample=1, alignment='@', word_code='B', force_signed=False, **kwargs):
        """:param words_per_sample: The number of words read from the file in each sample, default is 1
        :param alignment: One of the strings used by struct to indicate word endianness, default is system endianness
        :param word_code: The character code used by struct to indicate the word format and size, by default is unsigned bytes.
        :param force_signed: If set to True the final assembled value will be forced to be signed even if it was read from unsigned values"""
        self.words_per_sample = words_per_sample
        self.alignment = alignment
        self.word_code = word_code
        self.d = None

        def _signer(n):
            OFL = 1 << (words_per_sample*8)
            MAX = OFL >> 1
            if n >= MAX:
                n -= OFL
            return n

        def chunkwise(t, size=2):
            it = iter(t)
            return zip(*[it]*size)

        def id(x):
            return x

        if words_per_sample == 1:
            if a is not None:
                a = struct.unpack(alignment + (self.word_code*(len(a)//struct.calcsize(word_code))), a)
            if b is not None:
                b = struct.unpack(alignment + (self.word_code*(len(b)//struct.calcsize(word_code))), b)
        else:
            if alignment == ">" or alignment == "!" or (alignment in ['@', '='] and sys.byteorder != 'little'):
                aligner = id
            else:
                aligner = reversed

            if force_signed:
                signer = _signer
            else:
                signer = id

            if a is not None:
                a = [signer(reduce(lambda x, y: (x << 8) + y, aligner(v)))
                     for v in chunkwise(struct.unpack(alignment + ('B'*(len(a))), a), words_per_sample)]
            if b is not None:
                b = [signer(reduce(lambda x, y: (x << 8) + y, aligner(v)))
                     for v in chunkwise(struct.unpack(alignment + ('B'*(len(b))), b), words_per_sample)]

        super(DataEqualityComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a, b):
        if a is None and b is None:
            return (True, "Neither grain has a data payload", [])
        elif a is None:
            return (False, "{} is not set, but {} is binary data with length {}".format(self._identifier.format('a'),
                                                                                        self._identifier.format('b'),
                                                                                        len(b)))
        elif b is None:
            return (False, "{} is not set, but {} is binary data with length {}".format(self._identifier.format('b'),
                                                                                        self._identifier.format('a'),
                                                                                        len(a)))

        self.d = SequenceMatcher(None, a, b)
        print("!!!!!!!! {} !!!!!!!!\n\n".format(repr(self.d)))

        if self.d is None:
            print("SequenceMatcher failed to construct a diff for {!r}, and {!r}".format(a, b))

        if self.d.ratio() == 1.0:
            return (True, "Binary data {} are equal".format(self._identifier.format('<a/b>')), [])
        else:
            first_op = [x for x in self.d.get_opcodes() if x[0] is not 'equal'][0]
            i = first_op[1]
            if i < len(a) and i < len(b):
                msg = ("Binary data {} has similarity {} to {}, " +
                       "first different values are {}[{}] == {} and {}[{}] == {}").format(self._identifier.format('a'),
                                                                                          self.d.ratio(),
                                                                                          self._identifier.format('b'),
                                                                                          self._identifier.format('a'),
                                                                                          i,
                                                                                          a[i],
                                                                                          self._identifier.format('b'),
                                                                                          i,
                                                                                          b[i])
            elif i < len(a):
                msg = ("Binary data {} has similarity {} to {}, " +
                       "{} has {} extra values, starting with {}[{}] = {}").format(self._identifier.format('a'),
                                                                                   self.d.ratio(),
                                                                                   self._identifier.format('b'),
                                                                                   self._identifier.format('a'),
                                                                                   len(a) - len(b),
                                                                                   self._identifier.format('a'),
                                                                                   i,
                                                                                   a[i])
            else:
                msg = ("Binary data {} has similarity {} to {}, " +
                       "{} has {} extra values, starting with {}[{}] = {}").format(self._identifier.format('a'),
                                                                                   self.d.ratio(),
                                                                                   self._identifier.format('b'),
                                                                                   self._identifier.format('b'),
                                                                                   len(b) - len(a),
                                                                                   self._identifier.format('b'),
                                                                                   i,
                                                                                   b[i])
            return (False, msg, [])

    def _str(self, prefix=""):
        r = prefix
        if self.excluded():
            r += '\u25EF   '
        elif self.__bool__():
            r += '\u2705   '
        else:
            r += '\u274c   '
        r += self._msg
        if self.d is None:
            pass
        elif self.d.ratio() < 1.0:
            prefix += "  "
            opstrings = [prefix + "{:7}   a[{}:{}] --> b[{}:{}] {:>8} --> {}".format(tag, i1, i2, j1, j2,
                                                                                     '(' + ', '.join(str(x) for x in self.a[i1:i2]) + ')',
                                                                                     '(' + ', '.join(str(x) for x in self.b[i1:i2]) + ')')
                         for (tag, i1, i2, j1, j2) in self.d.get_opcodes()[:5]]
            r += '\n' + opstrings[0]
            if len(opstrings) > 1:
                r += '\n' + opstrings[1]
            if len(opstrings) > 2:
                r += '\n' + opstrings[2]
            if len(opstrings) > 3:
                r += '\n' + opstrings[3]
            if len(opstrings) > 4:
                r += '\n' + prefix + 'etc ...'
        return r


class DifferenceComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, expected_difference=0, **kwargs):
        self._expected_difference = expected_difference
        super(DifferenceComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a, b):
        opts = [option for option in self.ownoptions() if isinstance(option, ComparisonExpectDifferenceMatches)]
        diff = a - b
        if len(opts) == 0:
            if diff == self._expected_difference:
                return (True, "{} - {} == {!r} as expected".format(self._identifier.format('a'), self._identifier.format('b'), diff), [])
            else:
                return (False, "{} - {} == {!r}, not the expected {!r}".format(self._identifier.format('a'), self._identifier.format('b'), diff, self._expected_difference), [])
        else:
            if all(opt.matcher(diff) for opt in opts):
                return (True, "{} - {} == {!r}, meets requirements set in options".format(self._identifier.format('a'), self._identifier.format('b'), diff), [])
            else:
                return (False, "{} - {} == {!r}, does not meet requirements set in options".format(self._identifier.format('a'), self._identifier.format('b'), diff), [])


class TimestampDifferanceComparisonResult(DifferenceComparisonResult):
    def __init__(self, identifier, a, b, expected_difference=TimeOffset(0), **kwargs):
        super(TimestampDifferanceComparisonResult, self).__init__(identifier, a, b, expected_difference=expected_difference, **kwargs)


class AOnlyComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, **kwargs):
        super(AOnlyComparisonResult, self).__init__(identifier, a, None, **kwargs)

    def compare(self, a, b):
        return (False, "{} == {!r} but {} does not exist".format(self._identifier.format('a'), a, self._identifier.format('b')), [])


class BOnlyComparisonResult(ComparisonResult):
    def __init__(self, identifier, b, **kwargs):
        super(BOnlyComparisonResult, self).__init__(identifier, None, b, **kwargs)

    def compare(self, a, b):
        return (False, "{} does not exist, but {} == {!r}".format(self._identifier.format('a'), self._identifier.format('b'), b), [])


class OrderedContainerComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, comparison_class=EqualityComparisonResult, **kwargs):
        self._comparison_class = comparison_class
        super(OrderedContainerComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a, b):
        children = []

        children.append(EqualityComparisonResult('len({})'.format(self._identifier), len(a), len(b), options=self._options))
        for n in range(0, min(len(a), len(b))):
            children.append(self._comparison_class(self.identifier + "[{}]".format(n), a[n], b[n], options=self._options, key=n))
        if len(a) > len(b):
            for n in range(len(b), len(a)):
                children.append(AOnlyComparisonResult(self.identifier + "[{}]".format(n), a[n], options=self._options, key=n))
        if len(b) > len(a):
            for n in range(len(a), len(b)):
                children.append(BOnlyComparisonResult(self.identifier + "[{}]".format(n), b[n], options=self._options, key=n))

        if all(c or c.excluded() for c in children):
            return (True, "Lists match", children)
        else:
            return (False, "Lists do not match", children)


class MappingContainerComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, comparison_class=EqualityComparisonResult, **kwargs):
        self._comparison_class = comparison_class
        super(MappingContainerComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a, b):
        children = []

        for key in [k for k in a.keys() if k in b.keys()]:
            children.append(self._comparison_class(self.identifier + "[{!r}]".format(key), a[key], b[key], options=self._options, key=key))
        for key in [k for k in a.keys() if k not in b.keys()]:
            children.append(AOnlyComparisonResult(self.identifier + "[{!r}]".format(key), a[key], options=self._options, key=key))
        for key in [k for k in b.keys() if k not in a.keys()]:
            children.append(BOnlyComparisonResult(self.identifier + "[{!r}]".format(key), b[key], options=self._options, key=key))

        if all(c or c.excluded() for c in children):
            return (True, "Mappings match", children)
        else:
            return (False, "Mappings do not match", children)


class GrainComparisonResult(ComparisonResult):
    """A ComparisonResult class for comparing grains, this is where almost all of the grain comparison logic is contained."""
    def __init__(self, a, b, **kwargs):
        super(GrainComparisonResult, self).__init__("{}", a, b, **kwargs)

    def compare(self, a, b):
        children = {}

        for key in ['grain_type',
                    'source_id',
                    'flow_id',
                    'rate',
                    'duration',
                    'length']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)
        for key in ['origin_timestamp',
                    'sync_timestamp',
                    'creation_timestamp']:
            path = self._identifier + '.' + key
            children[key] = TimestampDifferanceComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

        children['timelabels'] = OrderedContainerComparisonResult(self._identifier + '.' + 'timelabels', a.timelabels, b.timelabels,
                                                                  options=self._options,
                                                                  comparison_class=MappingContainerComparisonResult,
                                                                  attr='timelabels')

        if a.grain_type != b.grain_type:
            # You can't compare the data of different types of grain sensibly
            self._options.append(Exclude.data)
            children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                       "grain types do not match",
                                                       attr="data",
                                                       options=self._options)

        elif a.grain_type == "event":
            # We are comparing event grains, so compare their event grain specific features
            for key in ['event_type',
                        'topic']:
                path = self._identifier + '.' + key
                children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)
            for key in ['event_data']:
                path = self._identifier + '.' + key
                children[key] = OrderedContainerComparisonResult(self._identifier + '.' + key, getattr(a, key), getattr(b, key),
                                                                 options=self._options,
                                                                 comparison_class=MappingContainerComparisonResult,
                                                                 attr=key)
            if children['event_type'].excluded() or children['topic'].excluded() or children['event_data'].excluded():
                children['length']._options.append(Exclude.length)

        elif a.grain_type == "audio":
            # We are comparing audio grains, so compare their audio grain specific features
            for key in ['format',
                        'samples',
                        'channels',
                        'sample_rate']:
                path = self._identifier + '.' + key
                children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

            if a.format == b.format:
                wps = 1
                s = False
                if a.format in [CogAudioFormat.S16_PLANES,
                                CogAudioFormat.S16_PAIRS,
                                CogAudioFormat.S16_INTERLEAVED]:
                    wc = 'h'
                elif a.format in [CogAudioFormat.S24_PLANES,
                                  CogAudioFormat.S24_PAIRS,
                                  CogAudioFormat.S24_INTERLEAVED]:
                    wc = 'B'
                    wps = 3
                    s = True
                elif a.format in [CogAudioFormat.S32_PLANES,
                                  CogAudioFormat.S32_PAIRS,
                                  CogAudioFormat.S32_INTERLEAVED]:
                    wc = 'i'
                elif a.format in [CogAudioFormat.S64_INVALID]:
                    wc = 'l'
                elif a.format in [CogAudioFormat.FLOAT_PLANES,
                                  CogAudioFormat.FLOAT_PAIRS,
                                  CogAudioFormat.FLOAT_INTERLEAVED]:
                    wc = 'f'
                elif a.format in [CogAudioFormat.DOUBLE_PLANES,
                                  CogAudioFormat.DOUBLE_PAIRS,
                                  CogAudioFormat.DOUBLE_INTERLEAVED]:
                    wc = 'd'
                else:
                    wc = 'B'

                children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data",
                                                                alignment="@",
                                                                word_code=wc,
                                                                words_per_sample=wps,
                                                                force_signed=s)
            else:
                self._options.append(Exclude.data)
                children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                           "payload formats do not match",
                                                           attr="data",
                                                           options=self._options)

        elif a.grain_type == "coded_audio":
            # We are comparing coded_audio grains, so compare their coded_audio grain specific features
            for key in ['format',
                        'samples',
                        'channels',
                        'sample_rate',
                        'priming',
                        'remainder']:
                path = self._identifier + '.' + key
                children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

            if a.format == b.format:
                children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data")
            else:
                self._options.append(Exclude.data)
                children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                           "payload formats do not match",
                                                           attr="data",
                                                           options=self._options)

        elif a.grain_type == "video":
            # We are comparing video grains, so compare their video grain specific features
            for key in ['format',
                        'width',
                        'height',
                        'layout']:
                path = self._identifier + '.' + key
                children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

            if a.format == b.format:
                if COG_FRAME_IS_COMPRESSED(a.format):
                    wc = 'B'
                elif a.format == CogFrameFormat.v210:
                    wc = 'I'
                elif a.format == CogFrameFormat.v216:
                    wc = 'H'
                elif COG_FRAME_IS_PACKED(a.format):
                    wc = 'B'
                else:
                    if COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 1:
                        wc = 'B'
                    elif COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 2:
                        wc = 'H'
                    elif COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 4:
                        wc = 'I'

                children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data",
                                                                alignment="@",
                                                                word_code=wc)
            else:
                self._options.append(Exclude.data)
                children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                           "payload formats do not match",
                                                           attr="data",
                                                           options=self._options)

        elif a.grain_type == "coded_video":
            # We are comparing coded_video grains, so compare their coded_video grain specific features
            for key in ['format',
                        'coded_width',
                        'coded_height',
                        'origin_width',
                        'origin_height',
                        'is_key_frame',
                        'temporal_offset',
                        'layout']:
                path = self._identifier + '.' + key
                children[key] = EqualityComparisonResult(path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

            for key in ['unit_offsets']:
                path = self._identifier + '.' + key
                children[key] = OrderedContainerComparisonResult(path,
                                                                 getattr(a, key),
                                                                 getattr(b, key),
                                                                 comparison_class=DifferenceComparisonResult,
                                                                 options=self._options, attr=key)

            if a.format == b.format:
                children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data")
            else:
                self._options.append(Exclude.data)
                children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                           "payload formats do not match",
                                                           attr="data",
                                                           options=self._options)

        else:
            # We are dealing with some weird unknown grain type, so just do a byte comparison of the data
            children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                            a.data,
                                                            b.data,
                                                            options=self._options,
                                                            attr="data")

        if len(children) > 0 and all(c or c.excluded() for (k, c) in children.items()):
            return (True, "Grains match", [c for (k, c) in children.items()])
        else:
            return (False, "Grains do not match", [c for (k, c) in children.items()])


class FailingComparisonResult(ComparisonResult):
    """A ComparisonResult that is always false, to represent trying to compare incomparable data"""
    def __init__(self, identifier, reason, **kwargs):
        self.reason = reason
        super(FailingComparisonResult, self).__init__(identifier, None, None, **kwargs)

    def compare(self, a, b):
        return (False, "Cannot compare {} and {} because: {}".format(self._identifier.format('a'),
                                                                     self._identifier.format('b'),
                                                                     self.reason), [])


#
# The ComparisonOption class and its descendents represent options that can be passed to the comparison mechanism to
# change how it behaves.
#
class ComparisonOption(object):
    def __init__(self, path):
        self.path = path

    def __ne__(self, other):
        return not (self == other)


class ComparisonExclude(ComparisonOption):
    def __repr__(self):
        return "Exclude" + self.path[2:]

    def __eq__(self, other):
        return type(self) == type(other) and self.path == other.path


class ComparisonExpectDifferenceMatches(ComparisonOption):
    def __init__(self, path, matcher, _repr):
        self.matcher = matcher
        self._repr = _repr
        super(ComparisonExpectDifferenceMatches, self).__init__(path)

    def __repr__(self):
        return self._repr


if __name__ == "__main__":
    from .testsignalgenerator import LumaSteps
    from uuid import uuid1

    src_id = uuid1()
    flow_id = uuid1()

    a = next(LumaSteps(src_id, flow_id, 1920, 1080))
    b = next(LumaSteps(src_id, flow_id, 1920, 1080))

    a.add_timelabel('tmp', 3, Fraction(25, 1))
    b.add_timelabel('tmp', 3, Fraction(25, 1))

    m = compare_grain(a, b,
                      Exclude.origin_timestamp,
                      Exclude.sync_timestamp,
                      Exclude.creation_timestamp)
    print(m)
    print(m.msg)
