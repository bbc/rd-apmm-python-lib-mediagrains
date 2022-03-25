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
from typing import Any, cast, Generic, Optional, Type, TypeVar, Union
from collections.abc import Iterable, MutableSequence

from ..grains import AudioGrain, CodedAudioGrain, CodedVideoGrain, EventGrain, Grain, VideoGrain

from mediatimestamp.immutable import TimeOffset, Timestamp
from difflib import SequenceMatcher

from functools import reduce
import struct
import sys

from ..cogenums import (CogAudioFormat, CogFrameFormat, COG_FRAME_IS_PACKED, COG_FRAME_IS_COMPRESSED,
                        COG_FRAME_FORMAT_BYTES_PER_VALUE)

from .options import Exclude, Include, ComparisonExclude, ComparisonExpectDifferenceMatches, \
    ComparisonOption, ComparisonPSNR
from .psnr import compute_psnr

CR = TypeVar('CR', bound='ComparisonResult')


#
# The ComparisonResult class and its descendents implement most of the actual comparison logic
#
class ComparisonResult(Generic[CR]):
    """
    Abstract base class for comparison results.

    public interface, attributes, all read only:

    identifier
        A string identifying what was being compared, will contain a single {} for substituting the
        name of the top level object
    attr
        An attribute name which identifies a sub-comparison within it's immediate parent. Is None when not a child.
    a
        The first object that was compared
    b
        The second object that was compared
    options
        A list of ComparisonOptions that include, exclude and expect differences on certain identifiers.
    children
        A list of ComparisonResult objects for sub-comparisons
    msg
        A human readable message to explain this result
    key
        Will be set when ComparisonResult is a sub-comparison of an OrderedContainerComparisonResult in which case
        the key will be a dictionary key, or a MappingContainerComparisonResult in which case the key will be an index.

    Subclasses should set _identifier and also implement compare.

    A ComparisonResult object itself is truthy if the comparison of a and b match,
    and falsy if they do not.
    """
    def __init__(self,
                 identifier: str,
                 a: object,
                 b: object,
                 options: Iterable[ComparisonOption] = [],
                 attr: Optional[str] = None, key: Optional[Union[int, str]] = None):
        self._a = a
        self._b = b
        self._identifier = identifier
        self._options = list(options)
        self._attr = attr
        self._key = key
        self._children: list[CR]
        (self._equal, self._msg, self._children) = self.compare(a, b)

    def __bool__(self) -> bool:
        """Allows for bool(ComparisonResult).

        :returns: returns a boolean value based on the result of the comparison of a and b."""
        return self._equal

    __nonzero__ = __bool__

    @property
    def attr(self) -> Optional[str]:
        return self._attr

    @property
    def key(self) -> Optional[Union[int, str]]:
        return self._key

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def a(self) -> object:
        return self._a

    @property
    def b(self) -> object:
        return self._b

    @property
    def children(self) -> list[CR]:
        return self._children

    @property
    def msg(self) -> str:
        """Human readable messages of any failing comparison and any failing sub-comparisons."""
        msgs = []
        msgs += ['(' + c.msg + ')' for c in self._children if not c and not c.excluded()]
        msgs += ['<IGNORING: ' + c.msg + '>' for c in self._children if not c and c.excluded()]
        if len(msgs) == 0:
            return self._msg
        else:
            return self._msg + ': ' + '; '.join(msgs)

    def excluded(self) -> bool:
        """Return a boolean value to show whether the identifier is Included or Excluded from the result."""
        return bool(len([
            option for option in self._options if isinstance(
                option, ComparisonExclude) and self._identifier == option.path]) != 0)

    def ownoptions(self) -> list[ComparisonOption]:
        """Return any ComparisonOptions to do with what is being compared in the ComparisonResult (identifier)."""
        return [option for option in self._options if self._identifier == option.path]

    def compare(self, a, b) -> tuple[bool, str, list[CR]]:
        """Override in subclasses to return a triple:
        (equal, msg, children)

        where:
          equal    - is True if a and b match and False otherwise
          msg      - is a human readable string explaining the matching
          children - is a list of comparison objects if this comparison was made
                     by combining other ones.
        """
        return (False, "A generic comparison always fails", [])

    def failing_attributes(self) -> list[str]:
        """Call to determine which attributes of the compared objects failed to match

        :returns: a list of strings, which are attribute names in the compared objects
        """
        return [c.attr for c in self.children if not c and c.attr is not None]

    def failing_keys(self) -> list[Union[int, str]]:
        """Call to determine which keys of the compared containers failed to match

        :returns: a list of strings, which are keys names in the compared containers
        """
        return [c.key for c in self.children if not c and c.key is not None]

    def _str(self, prefix="") -> str:
        """Pretty printed str of comparison and any sub-comparisons."""
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

    def __str__(self) -> str:
        return self._str()

    def __repr__(self) -> str:
        return "{}(identifier={!r}, a={!r}, b={!r}, options={!r})".format(
            self.__class__.__name__, self._identifier, self._a, self._b, self._options)

    def subcomparison_for_attribute(self, key: str) -> CR:
        """Search through sub-comparisons to find relevant child."""
        results = [c for c in self.children if c.attr == key]
        if len(results) == 0:
            raise KeyError("Key {!r} is not known in {!r}".format(key, self))
        else:
            return results[0]

    def __getattr__(self, key: str) -> CR:
        try:
            return self.subcomparison_for_attribute(key)
        except KeyError:
            raise AttributeError

    def subcomparison_for_key(self, key: Union[int, str]) -> CR:
        """Search through sub-comparisons to find relevant child."""
        results = [c for c in self.children if c.key == key]
        if len(results) == 0:
            raise KeyError
        else:
            return results[0]

    def __getitem__(self, key: Union[int, str]) -> CR:
        return self.subcomparison_for_key(key)


class EqualityComparisonResult(ComparisonResult):
    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        if a == b:
            return (True, "{} == {!r}".format(self._identifier.format('<a/b>'), a), [])
        else:
            return (False, "{} == {!r}, {} == {!r} no match".format(
                self._identifier.format('a'), a, self._identifier.format('b'), b), [])


class DataEqualityComparisonResult(ComparisonResult):
    """This comparison result is used for comparing long data strings to each other, and provides useful information
    like the first byte at which they differ"""
    def __init__(self,
                 identifier: str, a, b,
                 words_per_sample: int = 1,
                 alignment: str = '@',
                 word_code: str = 'B',
                 force_signed: bool = False,
                 **kwargs):
        """:param words_per_sample: The number of words read from the file in each sample, default is 1
        :param alignment: One of the strings used by struct to indicate word endianness, default is system endianness
        :param word_code: The character code used by struct to indicate the word format and size, by default is
                          unsigned bytes.
        :param force_signed: If set to True the final assembled value will be forced to be signed even if it was read
                             from unsigned values"""
        self.words_per_sample = words_per_sample
        self.alignment = alignment
        self.word_code = word_code
        self.d: Optional[SequenceMatcher] = None

        # a and b might be various types of objects that can be converted into bytes objects, this ensures they are
        # simple bytes objects
        if a is not None:
            a = bytes(a)
        if b is not None:
            b = bytes(b)

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

    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        if a is None and b is None:
            return (True, "Neither grain has a data payload", [])
        elif a is None:
            return (False, "{} is not set, but {} is binary data with length {}".format(self._identifier.format('a'),
                                                                                        self._identifier.format('b'),
                                                                                        len(b)), [])
        elif b is None:
            return (False, "{} is not set, but {} is binary data with length {}".format(self._identifier.format('b'),
                                                                                        self._identifier.format('a'),
                                                                                        len(a)), [])

        if self.excluded():
            return (False, "For speed reasons not comparing {} and {} when this would be excluded".format(
                self._identifier.format('a'), self._identifier.format('b')), [])

        self.d = SequenceMatcher(None, a, b)
        if self.d.ratio() == 1.0:
            return (True, "Binary data {} are equal".format(self._identifier.format('<a/b>')), [])
        else:
            first_op = [x for x in self.d.get_opcodes() if x[0] != 'equal'][0]
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

    # Ignoring typing on lines below as: error: Value of type "object" is not indexable
    def _str(self, prefix="") -> str:
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
            opstrings = [prefix + "{:7}   a[{}:{}] --> b[{}:{}] {:>8} --> {}".format(
                            tag, i1, i2, j1, j2, '(' + ', '.join(str(x) for x in self.a[i1:i2]) + ')',  # type: ignore
                            '(' + ', '.join(str(x) for x in self.b[i1:i2]) + ')')  # type: ignore
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
    """Compare any two objects that can be subtracted from eachother"""
    def __init__(self, identifier: str, a, b, expected_difference=0, **kwargs):
        self._expected_difference = expected_difference
        super(DifferenceComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        opts = [option for option in self.ownoptions() if isinstance(option, ComparisonExpectDifferenceMatches)]
        diff = a - b
        if len(opts) == 0:
            if diff == self._expected_difference:
                return (True, "{} - {} == {!r} as expected".format(
                    self._identifier.format('a'), self._identifier.format('b'), diff), [])
            else:
                return (False, "{} - {} == {!r}, not the expected {!r}".format(
                    self._identifier.format('a'), self._identifier.format('b'), diff, self._expected_difference), [])
        else:
            if all(opt.matcher(diff) for opt in opts):
                return (True, "{} - {} == {!r}, meets requirements set in options".format(
                    self._identifier.format('a'), self._identifier.format('b'), diff), [])
            else:
                return (False, "{} - {} == {!r}, does not meet requirements set in options".format(
                    self._identifier.format('a'), self._identifier.format('b'), diff), [])


class TimestampDifferenceComparisonResult(DifferenceComparisonResult):
    def __init__(self,
                 identifier: str,
                 a: Timestamp,
                 b: Timestamp,
                 expected_difference: TimeOffset = TimeOffset(0),
                 **kwargs):
        super(TimestampDifferenceComparisonResult, self).__init__(
            identifier, a, b, expected_difference=expected_difference, **kwargs)


class PSNRComparisonResult(ComparisonResult):
    def __init__(self, identifier: str, a: Grain, b: Grain, **kwargs):
        """Compute the PSNR for two grains and compare the result with the expected values and comparison operator.

        :param identifier: The path in the grain structure
        :param a: A Grain
        :param b: Another Grain
        :param kwargs: Other named arguments
        """
        super(PSNRComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a: Grain, b: Grain) -> tuple[bool, str, list[ComparisonResult]]:
        opts = [
            option for option in self._options if isinstance(option, ComparisonPSNR) and self.identifier == option.path
            ]

        if self.excluded():
            return (False, "For speed reasons not comparing {} and {} when this would be excluded".format(
                self._identifier.format('a'), self._identifier.format('b')), [])

        try:
            psnr = compute_psnr(a, b)
        except NotImplementedError:
            return (False, "Grain is not supported for PSNR comparison of {} and {}".format(
                self._identifier.format('a'), self._identifier.format('b')), [])

        if all(opt.matcher(psnr) for opt in opts):
            return (True, "PSNR({}, {}) == {!r}, meets requirements set in options".format(
                    self._identifier.format('a'), self._identifier.format('b'), psnr), [])
        else:
            return (False, "PSNR({}, {}) == {!r}, does not meet requirements set in options".format(
                    self._identifier.format('a'), self._identifier.format('b'), psnr), [])


class AOnlyComparisonResult(ComparisonResult):
    """Used when comparing containers such as lists, dicts and Grain Iterators where an identifier exists in
    object A but not in object B. In this case we report back the existence of a difference in identifiers
    between the objects. For example lists of different lengths, or dicts with differing keys."""
    def __init__(self, identifier: str, a, **kwargs):
        super(AOnlyComparisonResult, self).__init__(identifier, a, None, **kwargs)

    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        return (False, "{} == {!r} but {} does not exist".format(
            self._identifier.format('a'), a, self._identifier.format('b')), [])


class BOnlyComparisonResult(ComparisonResult):
    """Used when comparing containers such as lists, dicts and Grain Iterators where an identifier exists in
    object B but not in object A. In this case we report back the existence of a difference in identifiers
    between the objects. For example lists of different lengths, or dicts with differing keys."""
    def __init__(self, identifier: str, b, **kwargs):
        super(BOnlyComparisonResult, self).__init__(identifier, None, b, **kwargs)

    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        return (
            False,
            "{} does not exist, but {} == {!r}".format(
                self._identifier.format('a'), self._identifier.format('b'), b), [])


class OrderedContainerComparisonResult(ComparisonResult):
    """Compare two mutable sequences (lists) using the comparison_class to define the comparison method."""
    def __init__(self,
                 identifier: str,
                 a: MutableSequence[Any],
                 b: MutableSequence[Any],
                 comparison_class: Type[ComparisonResult] = EqualityComparisonResult,
                 **kwargs):
        self._comparison_class = comparison_class
        super(OrderedContainerComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a: MutableSequence[Any], b: MutableSequence[Any]) -> tuple[bool, str, list[ComparisonResult]]:
        children: list[ComparisonResult] = []

        children.append(EqualityComparisonResult(
            'len({})'.format(self._identifier), len(a), len(b), options=self._options))
        for n in range(0, min(len(a), len(b))):
            children.append(self._comparison_class(
                self.identifier + "[{}]".format(n), a[n], b[n], options=self._options, key=n))
        if len(a) > len(b):
            for n in range(len(b), len(a)):
                children.append(AOnlyComparisonResult(
                    self.identifier + "[{}]".format(n), a[n], options=self._options, key=n))
        if len(b) > len(a):
            for n in range(len(a), len(b)):
                children.append(BOnlyComparisonResult(
                    self.identifier + "[{}]".format(n), b[n], options=self._options, key=n))

        if all(c or c.excluded() for c in children):
            return (True, "Lists match", children)
        else:
            return (False, "Lists do not match", children)


class GrainIteratorComparisonResult(ComparisonResult):
    def __init__(self,
                 identifier: str,
                 a: Iterable[Grain],
                 b: Iterable[Grain],
                 return_last_only: bool = False,
                 **kwargs):
        self.return_last_only = return_last_only
        super(GrainIteratorComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a: Iterable[Grain], b: Iterable[Grain]) -> tuple[bool, str, list[ComparisonResult]]:
        a = iter(a)
        b = iter(b)

        self.compared_item_count: int = 0
        all_success = True

        children: list[ComparisonResult] = []

        while True:
            A = next(a, None)
            B = next(b, None)

            if A is None and B is None:
                break
            elif A is None:
                children.append(BOnlyComparisonResult("{}", B, options=self._options, key=self.compared_item_count))
                all_success = False
                break
            elif B is None:
                children.append(AOnlyComparisonResult("{}", A, options=self._options, key=self.compared_item_count))
                all_success = False
                break
            else:
                comparison_result = GrainComparisonResult(
                    "{}", A, B, options=self._options, key=self.compared_item_count)
                self.compared_item_count += 1

                if self.return_last_only:
                    last_comparison = comparison_result
                else:
                    children.append(comparison_result)

                if not comparison_result:
                    all_success = False
                    break

        if self.return_last_only and last_comparison is not None:
            children.append(last_comparison)

        if all_success:
            return (
                True,
                "Iterators Match with length {}".format(self.compared_item_count),
                children
            )
        else:
            return (
                False,
                "Iterators differ first at entry {}".format(self.compared_item_count),
                children
            )

    def __len__(self) -> int:
        return self.compared_item_count


class MappingContainerComparisonResult(ComparisonResult):
    """Compare two dicts using the comparison_class to define the comparison method."""
    def __init__(self,
                 identifier: str,
                 a: dict[Any, Any],
                 b: dict[Any, Any],
                 comparison_class: Type[ComparisonResult] = EqualityComparisonResult,
                 **kwargs):
        self._comparison_class = comparison_class
        super(MappingContainerComparisonResult, self).__init__(identifier, a, b, **kwargs)

    def compare(self, a: dict[Any, Any], b: dict[Any, Any]) -> tuple[bool, str, list[ComparisonResult]]:
        children: list[ComparisonResult] = []

        for key in [k for k in a.keys() if k in b.keys()]:
            children.append(self._comparison_class(
                self.identifier + "[{!r}]".format(key), a[key], b[key], options=self._options, key=key))
        for key in [k for k in a.keys() if k not in b.keys()]:
            children.append(AOnlyComparisonResult(
                self.identifier + "[{!r}]".format(key), a[key], options=self._options, key=key))
        for key in [k for k in b.keys() if k not in a.keys()]:
            children.append(BOnlyComparisonResult(
                self.identifier + "[{!r}]".format(key), b[key], options=self._options, key=key))

        if all(c or c.excluded() for c in children):
            return (True, "Mappings match", children)
        else:
            return (False, "Mappings do not match", children)


class GrainComparisonResult(ComparisonResult):
    """A ComparisonResult class for comparing grains, this is where almost all of the grain comparison logic is
    contained."""
    def compare_event_grains(self, a: EventGrain, b: EventGrain, children) -> None:
        # We are comparing event grains, so compare their event grain specific features
        for key in ['event_type',
                    'topic']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)
        for key in ['event_data']:
            path = self._identifier + '.' + key
            children[key] = OrderedContainerComparisonResult(
                self._identifier + '.' + key,
                getattr(a, key),
                getattr(b, key),
                options=self._options,
                comparison_class=MappingContainerComparisonResult,
                attr=key)
        if children['event_type'].excluded() or children['topic'].excluded() or children['event_data'].excluded():
            children['length']._options.append(Exclude.length)

    def compare_audio_grains(self, a: AudioGrain, b: AudioGrain, children) -> None:
        # We are comparing audio grains, so compare their audio grain specific features
        for key in ['format',
                    'samples',
                    'channels',
                    'sample_rate']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

        if a.format == b.format:
            path = self._identifier + '.data'
            compare_psnr = len(
                [option for option in self._options if isinstance(option, ComparisonPSNR) and path == option.path]
                ) != 0
            if compare_psnr:
                children['data'] = PSNRComparisonResult(path,
                                                        a,
                                                        b,
                                                        options=self._options)
            else:
                words_per_sample = 1
                force_signed = False
                if a.format in [CogAudioFormat.S16_PLANES,
                                CogAudioFormat.S16_PAIRS,
                                CogAudioFormat.S16_INTERLEAVED]:
                    word_code = 'h'
                elif a.format in [CogAudioFormat.S24_PLANES,
                                  CogAudioFormat.S24_PAIRS,
                                  CogAudioFormat.S24_INTERLEAVED]:
                    word_code = 'B'
                    words_per_sample = 3
                    force_signed = True
                elif a.format in [CogAudioFormat.S32_PLANES,
                                  CogAudioFormat.S32_PAIRS,
                                  CogAudioFormat.S32_INTERLEAVED]:
                    word_code = 'i'
                elif a.format in [CogAudioFormat.S64_INVALID]:
                    word_code = 'l'
                elif a.format in [CogAudioFormat.FLOAT_PLANES,
                                  CogAudioFormat.FLOAT_PAIRS,
                                  CogAudioFormat.FLOAT_INTERLEAVED]:
                    word_code = 'f'
                elif a.format in [CogAudioFormat.DOUBLE_PLANES,
                                  CogAudioFormat.DOUBLE_PAIRS,
                                  CogAudioFormat.DOUBLE_INTERLEAVED]:
                    word_code = 'd'
                else:
                    word_code = 'B'

                children['data'] = DataEqualityComparisonResult(path,
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data",
                                                                alignment="@",
                                                                word_code=word_code,
                                                                words_per_sample=words_per_sample,
                                                                force_signed=force_signed)
        else:
            self._options.append(Exclude.data)
            children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                       "payload formats do not match",
                                                       attr="data",
                                                       options=self._options)

    def compare_coded_audio_grains(self, a: CodedAudioGrain, b: CodedAudioGrain, children) -> None:
        # We are comparing coded_audio grains, so compare their coded_audio grain specific features
        for key in ['format',
                    'samples',
                    'channels',
                    'sample_rate',
                    'priming',
                    'remainder']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

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

    def compare_video_grains(self, a: VideoGrain, b: VideoGrain, children) -> None:
        # We are comparing video grains, so compare their video grain specific features
        for key in ['format',
                    'width',
                    'height',
                    'layout']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

        if a.format == b.format:
            path = self._identifier + '.data'
            compare_psnr = len(
                [option for option in self._options if isinstance(option, ComparisonPSNR) and path == option.path]
                ) != 0
            if compare_psnr:
                children['data'] = PSNRComparisonResult(path,
                                                        a,
                                                        b,
                                                        options=self._options)
            else:
                if COG_FRAME_IS_COMPRESSED(a.format):
                    word_code = 'B'
                elif a.format == CogFrameFormat.v210:
                    word_code = 'I'
                elif a.format == CogFrameFormat.v216:
                    word_code = 'H'
                elif COG_FRAME_IS_PACKED(a.format):
                    word_code = 'B'
                else:
                    if COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 1:
                        word_code = 'B'
                    elif COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 2:
                        word_code = 'H'
                    elif COG_FRAME_FORMAT_BYTES_PER_VALUE(a.format) == 4:
                        word_code = 'I'

                children['data'] = DataEqualityComparisonResult(self._identifier + ".data",
                                                                a.data,
                                                                b.data,
                                                                options=self._options,
                                                                attr="data",
                                                                alignment="@",
                                                                word_code=word_code)
        else:
            self._options.append(Exclude.data)
            children['data'] = FailingComparisonResult(self._identifier + ".data",
                                                       "payload formats do not match",
                                                       attr="data",
                                                       options=self._options)

    def compare_coded_video_grains(self, a: CodedVideoGrain, b: CodedVideoGrain, children) -> None:
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
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

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

    def compare(self, a: Grain, b: Grain) -> tuple[bool, str, list[ComparisonResult]]:
        children: dict[str, ComparisonResult] = {}

        if Include.creation_timestamp not in self._options:
            self._options.append(Exclude.creation_timestamp)

        for key in ['grain_type',
                    'source_id',
                    'flow_id',
                    'rate',
                    'duration',
                    'length']:
            path = self._identifier + '.' + key
            children[key] = EqualityComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)
        for key in ['origin_timestamp',
                    'sync_timestamp',
                    'creation_timestamp']:
            path = self._identifier + '.' + key
            children[key] = TimestampDifferenceComparisonResult(
                path, getattr(a, key), getattr(b, key), options=self._options, attr=key)

        children['timelabels'] = OrderedContainerComparisonResult(
            self._identifier + '.' + 'timelabels',
            a.timelabels,
            b.timelabels,
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
            self.compare_event_grains(cast(EventGrain, a), cast(EventGrain, b), children)

        elif a.grain_type == "audio":
            self.compare_audio_grains(cast(AudioGrain, a), cast(AudioGrain, b), children)

        elif a.grain_type == "coded_audio":
            self.compare_coded_audio_grains(cast(CodedAudioGrain, a), cast(CodedAudioGrain, b), children)

        elif a.grain_type == "video":
            self.compare_video_grains(cast(VideoGrain, a), cast(VideoGrain, b), children)

        elif a.grain_type == "coded_video":
            self.compare_coded_video_grains(cast(CodedVideoGrain, a), cast(CodedVideoGrain, b), children)

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
    def __init__(self, identifier: str, reason: str, **kwargs):
        self.reason = reason
        super(FailingComparisonResult, self).__init__(identifier, None, None, **kwargs)

    def compare(self, a, b) -> tuple[bool, str, list[ComparisonResult]]:
        return (False, "Cannot compare {} and {} because: {}".format(self._identifier.format('a'),
                                                                     self._identifier.format('b'),
                                                                     self.reason), [])
