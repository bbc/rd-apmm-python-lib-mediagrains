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

"""Options can be passed to comparisons which are constructed using the objects Exclude, Include, and ExpectedDifference.
These three objects provide a convenient (and similar) interface. By accessing attributes of these objects that have
the same names as attributes of the objects to be compared you can identify which attributes to refer to.

eg.

options.Include.creation_timestamp

is an option that causes the comparison operation to not ignore any differences in the creation_timestamp member of the compared
objects.

If an Include and an Exclude are used for the same attribute then the Exclude takes precedence. At present the only real use for Include is
to override the default behaviour that ignores creation_timestamp differences.

For options.ExpectedDifference there is an additional step, which is to apply comparison operations, so:

(options.ExpectedDifference.creation_timestamp > TimeOffset(0, 64))

is an option that requires (a.creation_timestamp - b.creation_timestamp) to be greater than 64 nanoseconds.

This mechanism may be expanded for further option types in the future.


CompareOnlyMetadata is a convenience name for Exclude.data"""

__all__ = ["Exclude", "Include", "ExpectedDifference", "CompareOnlyMetadata", "PSNR"]


#
# Primarily as syntactic sugar the Exclude and ExpectedDifference objects
# are exported to make it easier to construct ComparisonOptions in a simple fashion
#
class _Exclude(object):
    def __getattr__(self, attr):
        return ComparisonExclude("{}." + attr)


class _Include(object):
    def __getattr__(self, attr):
        return ComparisonInclude("{}." + attr)


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
            raise ValueError(("{!r} & {!r} is not a valid operation: " +
                              "When combining ExpectedDifference operations with & they must refer to the same attribute").format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(self.path, lambda x: self.matcher(x) and other.matcher(x), "{!r} & {!r}".format(self, other))

    def __or__(self, other):
        if not isinstance(other, ComparisonExpectDifferenceMatches):
            raise ValueError("{!r} | {!r} is not a valid operation".format(self, other))
        elif other.path != self.path:
            raise ValueError(("{!r} | {!r} is not a valid operation: " +
                              "When combining ExpectedDifference operations with | they must refer to the same attribute").format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(self.path, lambda x: self.matcher(x) or other.matcher(x), "{!r} | {!r}".format(self, other))

    def __getattr__(self, attr):
        return _ExpectedDifference(self.path + "." + attr)


class _PSNR(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return self.path.format("PSNR")

    def __lt__(self, other):
        def _compare_psnr(x, other):
            for comp_x, comp_other in zip(x, other):
                if comp_other is not None and not comp_x < comp_other:
                    return False
            return True

        return ComparisonPSNR(self.path, lambda x: _compare_psnr(x, other), "{} < {!r}".format('PSNR', other))

    def __le__(self, other):
        def _compare_psnr(x, other):
            for comp_x, comp_other in zip(x, other):
                if comp_other is not None and not comp_x <= comp_other:
                    return False
            return True

        return ComparisonPSNR(self.path, lambda x: _compare_psnr(x, other), "{} <= {!r}".format('PSNR', other))

    def __gt__(self, other):
        def _compare_psnr(x, other):
            for comp_x, comp_other in zip(x, other):
                if comp_other is not None and not comp_x > comp_other:
                    return False
            return True

        return ComparisonPSNR(self.path, lambda x: _compare_psnr(x, other), "{} > {!r}".format('PSNR', other))

    def __ge__(self, other):
        def _compare_psnr(x, other):
            for comp_x, comp_other in zip(x, other):
                if comp_other is not None and not comp_x >= comp_other:
                    return False
            return True

        return ComparisonPSNR(self.path, lambda x: _compare_psnr(x, other), "{} >= {!r}".format('PSNR', other))

    def __getattr__(self, attr):
        return _PSNR(self.path + "." + attr)


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


class ComparisonInclude(ComparisonOption):
    def __repr__(self):
        return "Include" + self.path[2:]

    def __eq__(self, other):
        return type(self) == type(other) and self.path == other.path


class ComparisonExpectDifferenceMatches(ComparisonOption):
    def __init__(self, path, matcher, _repr):
        self.matcher = matcher
        self._repr = _repr
        super(ComparisonExpectDifferenceMatches, self).__init__(path)

    def __repr__(self):
        return self._repr


class ComparisonPSNR(ComparisonOption):
    def __init__(self, path, matcher, _repr):
        self.matcher = matcher
        self._repr = _repr
        super(ComparisonPSNR, self).__init__(path)

    def __repr__(self):
        return self._repr


Exclude = _Exclude()


Include = _Include()


ExpectedDifference = _ExpectedDifference("{}")


CompareOnlyMetadata = Exclude.data


PSNR = _PSNR("{}")
