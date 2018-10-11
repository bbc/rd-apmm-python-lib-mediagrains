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
"""

from __future__ import print_function
from __future__ import absolute_import

from fractions import Fraction
from mediatimestamp import TimeOffset

__all__ = ["compare_grain", "Exclude"]


class ComparisonResult (object):
    """
    Abstract base class for comparison results.

    public interface, attributes, all read only:

    identifier -- an identifier identifing what was being compared, will contain a single {} for substituting the name of the top level object
    a -- the first object that was compared
    b -- the second object that was compared
    children -- a list of ComparisonResult objects for sub-comparisons
    msg -- a human readable message to explain this result

    subclasses should set _identifier and also implement compare.

    in addition the object itself is truthy if the comparison of a and b match,
    and falsy if they do not.
    """
    def __init__(self, identifier, a, b, exclude_paths=[]):
        self._a = a
        self._b = b
        self._identifier = identifier
        self._exclude_paths = exclude_paths
        (self._equal, self._msg, self._children) = self.compare(a, b)

    def __bool__(self):
        return self._equal

    __nonzero__ = __bool__

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
        return self._identifier in self._exclude_paths

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

    def _str(self, prefix=""):
        r = prefix
        if self._identifier in self._exclude_paths:
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
        return "{}(identifier={!r}, a={!r}, b={!r}, exclude_paths={!r})".format(self.__class__.__name__, self._identifier, self._a, self._b, self._exclude_paths)


class EqualityComparisonResult(ComparisonResult):
    def compare(self, a, b):
        if a == b:
            return (True, "{} == {!r}".format(self._identifier.format('<a/b>'), a), [])
        else:
            return (False, "{} == {!r}, {} == {!r} no match".format(self._identifier.format('a'), a, self._identifier.format('b'), b), [])


class DifferenceComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, exclude_paths=[], expected_difference=0):
        self._expected_difference = expected_difference
        super(DifferenceComparisonResult, self).__init__(identifier, a, b, exclude_paths=exclude_paths)

    def compare(self, a, b):
        diff = a - b
        if diff == self._expected_difference:
            return (True, "{} - {} == {!r} as expected".format(self._identifier.format('a'), self._identifier.format('b'), diff), [])
        else:
            return (False, "{} - {} == {!r}, not the expected {!r}".format(self._identifier.format('a'), self._identifier.format('b'), diff, self._expected_difference), [])


class TimestampDifferanceComparisonResult(DifferenceComparisonResult):
    def __init__(self, identifier, a, b, exclude_paths=[], expected_difference=TimeOffset(0)):
        super(TimestampDifferanceComparisonResult, self).__init__(identifier, a, b, expected_difference=expected_difference, exclude_paths=exclude_paths)


class AOnlyComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, exclude_paths=[]):
        super(AOnlyComparisonResult, self).__init__(identifier, a, None, exclude_paths=exclude_paths)

    def compare(self, a, b):
        return (False, "{} == {!r} but {} does not exist".format(self._identifier.format('a'), a, self._identifier.format('b')), [])


class BOnlyComparisonResult(ComparisonResult):
    def __init__(self, identifier, b, exclude_paths=[]):
        super(BOnlyComparisonResult, self).__init__(identifier, None, b, exclude_paths=exclude_paths)

    def compare(self, a, b):
        return (False, "{} does not exist, but {} == {!r}".format(self._identifier.format('a'), self._identifier.format('b'), b), [])


class OrderedContainerComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, exclude_paths=[], comparison_class=EqualityComparisonResult):
        self._comparison_class = comparison_class
        super(OrderedContainerComparisonResult, self).__init__(identifier, a, b, exclude_paths=exclude_paths)

    def compare(self, a, b):
        children = []

        children.append(EqualityComparisonResult('len({})'.format(self._identifier), len(a), len(b), exclude_paths=self._exclude_paths))
        for n in range(0, min(len(a), len(b))):
            children.append(self._comparison_class(self.identifier + "[{}]".format(n), a[n], b[n], exclude_paths=self._exclude_paths))
        if len(a) > len(b):
            for n in range(len(b), len(a)):
                children.append(AOnlyComparisonResult(self.identifier + "[{}]".format(n), a[n], exclude_paths=self._exclude_paths))
        if len(b) > len(a):
            for n in range(len(a), len(b)):
                children.append(BOnlyComparisonResult(self.identifier + "[{}]".format(n), b[n], exclude_paths=self._exclude_paths))

        if all(c or c.excluded() for c in children):
            return (True, "Lists match", children)
        else:
            return (False, "Lists do not match", children)


class MappingContainerComparisonResult(ComparisonResult):
    def __init__(self, identifier, a, b, exclude_paths=[], comparison_class=EqualityComparisonResult):
        self._comparison_class = comparison_class
        super(MappingContainerComparisonResult, self).__init__(identifier, a, b, exclude_paths=exclude_paths)

    def compare(self, a, b):
        children = []

        children.append(OrderedContainerComparisonResult('list({}.keys())'.format(self._identifier), list(a.keys()), list(b.keys()), exclude_paths=self._exclude_paths))
        for key in [k for k in a.keys() if k in b.keys()]:
            children.append(self._comparison_class(self.identifier + "[{!r}]".format(key), a[key], b[key], exclude_paths=self._exclude_paths))
        for key in [k for k in a.keys() if k not in b.keys()]:
            children.append(AOnlyComparisonResult(self.identifier + "[{!r}]".format(key), a[key], exclude_paths=self._exclude_paths))
        for key in [k for k in b.keys() if k not in a.keys()]:
            children.append(BOnlyComparisonResult(self.identifier + "[{!r}]".format(key), b[key], exclude_paths=self._exclude_paths))

        if all(c or c.excluded() for c in children):
            return (True, "Mappings match", children)
        else:
            return (False, "Mappings do not match", children)


class GrainComparisonResult(ComparisonResult):
    def __init__(self, a, b, exclude_paths=[]):
        super(GrainComparisonResult, self).__init__("{}", a, b, exclude_paths=exclude_paths)

    def compare(self, a, b):
        children = []

        for key in ['grain_type',
                    'source_id',
                    'flow_id',
                    'rate',
                    'duration',
                    'length']:
            path = self._identifier + '.' + key
            children.append(EqualityComparisonResult(path, getattr(a, key), getattr(b, key), exclude_paths=self._exclude_paths))
        for key in ['origin_timestamp',
                    'sync_timestamp',
                    'creation_timestamp']:
            path = self._identifier + '.' + key
            children.append(TimestampDifferanceComparisonResult(path, getattr(a, key), getattr(b, key), exclude_paths=self._exclude_paths))

        if self._identifier + '.' + 'timelabels' not in self._exclude_paths:
            children.append(OrderedContainerComparisonResult(self._identifier + '.' + 'timelabels', a.timelabels, b.timelabels,
                                                             exclude_paths=self._exclude_paths,
                                                             comparison_class=MappingContainerComparisonResult))

        if a.grain_type == "event" and b.grain_type == "event":
            # We are comparing event grains, so compare their event grain specific features
            for key in ['event_type',
                        'topic']:
                path = self._identifier + '.' + key
                children.append(EqualityComparisonResult(path, getattr(a, key), getattr(b, key), exclude_paths=self._exclude_paths))
            for key in ['event_data']:
                path = self._identifier + '.' + key
                children.append(OrderedContainerComparisonResult(self._identifier + '.' + key, getattr(a, key), getattr(b, key),
                                                                 exclude_paths=self._exclude_paths,
                                                                 comparison_class=MappingContainerComparisonResult))

        if len(children) > 0 and all(c or c.excluded() for c in children):
            return (True, "Grains match", children)
        else:
            return (False, "Grains do not match", children)


class ComparisonOption(object):
    def __init__(self, path):
        self.path = path


class ComparisonExclude(ComparisonOption):
    pass


class Exclude(object):
    grain_type = ComparisonExclude("{}.grain_type")
    source_id = ComparisonExclude("{}.source_id")
    flow_id = ComparisonExclude("{}.flow_id")
    rate = ComparisonExclude("{}.rate")
    duration = ComparisonExclude("{}.duration")
    length = ComparisonExclude("{}.length")
    origin_timestamp = ComparisonExclude("{}.origin_timestamp")
    sync_timestamp = ComparisonExclude("{}.sync_timestamp")
    creation_timestamp = ComparisonExclude("{}.creation_timestamp")
    timelabels = ComparisonExclude("{}.timelabels")


def compare_grain(a, b, *options):
    exclude_paths = [option.path for option in options if isinstance(option, ComparisonExclude)]
    return GrainComparisonResult(a, b, exclude_paths=exclude_paths)


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
