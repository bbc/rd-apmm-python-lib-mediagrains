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

"""Please refer to the README for in-depth information on how to use options in practice.
The Options make it easy to exclude, include and expect differences between different identifiers.
Primarily as syntactic sugar the Exclude and ExpectedDifference objects are exported to make it easier to construct
ComparisonOptions in a simple fashion.

This code is difficult to explain in-line, hence, lets demonstrate how an exclude works.
An example invocation:

>>> from mediagrains.comparison.options import Exclude
>>> compare_grain(a, b, Exclude.creation_timestamp)

Exclude is an exported variable that is assigned to create an object of the _Exclude() class.
_Exclude defines a __getattr__ method, the attribute used in the invocation (creation_timestamp) triggers this method.
The __getattr__ creates a ComparisonExclude object which in turn triggers the __init__ of its super ComparisonOption.
The __init__ of ComparisonOption is passed a path, which is ("{}." + attr), so in this case it's
"{}.creation_timestamp", and stores it in a variable called path.
The ComparisonExclude object is returned, this defines a __repr__ and __eq__ for an exclude option with the given path.

It is then possible to see how the options are used for result filtering in the excluded and ownoptions
methods in ComparisonResult by seeing if the path matches the identifier and the type of ComparisonOption.

Include, ExpectedDifference and PSNR behave similarly.

CompareOnlyMetadata is a convenience name for Exclude.data
"""

__all__ = ["Exclude", "Include", "ExpectedDifference", "CompareOnlyMetadata", "PSNR"]


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
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x == other, "{} == {!r}".format(self.path.format('ExpectedDifference'), other))

    def __ne__(self, other):
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x != other, "{} != {!r}".format('ExpectedDifference', other))

    def __lt__(self, other):
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x < other, "{} < {!r}".format('ExpectedDifference', other))

    def __le__(self, other):
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x <= other, "{} <= {!r}".format('ExpectedDifference', other))

    def __gt__(self, other):
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x > other, "{} > {!r}".format('ExpectedDifference', other))

    def __ge__(self, other):
        return ComparisonExpectDifferenceMatches(
            self.path, lambda x: x >= other, "{} >= {!r}".format('ExpectedDifference', other))

    def __and__(self, other):
        if not isinstance(other, ComparisonExpectDifferenceMatches):
            raise ValueError("{!r} & {!r} is not a valid operation".format(self, other))
        elif other.path != self.path:
            raise ValueError(("{!r} & {!r} is not a valid operation: " +
                              "When combining ExpectedDifference operations with & they must refer to the same " +
                              "attribute"
                              ).format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(
                self.path, lambda x: self.matcher(x) and other.matcher(x), "{!r} & {!r}".format(self, other))

    def __or__(self, other):
        if not isinstance(other, ComparisonExpectDifferenceMatches):
            raise ValueError("{!r} | {!r} is not a valid operation".format(self, other))
        elif other.path != self.path:
            raise ValueError(("{!r} | {!r} is not a valid operation: " +
                              "When combining ExpectedDifference operations with | they must refer to the same " +
                              "attribute"
                              ).format(self, other))
        else:
            return ComparisonExpectDifferenceMatches(
                self.path, lambda x: self.matcher(x) or other.matcher(x), "{!r} | {!r}".format(self, other))

    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            raise AttributeError
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
        if attr.startswith('__') and attr.endswith('__'):
            raise AttributeError
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
