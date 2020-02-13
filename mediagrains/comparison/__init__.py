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
"""

from ._internal import GrainComparisonResult, GrainIteratorComparisonResult
from .psnr import compute_psnr

__all__ = ["compare_grain", "compute_psnr"]


#
# The compare_grain method is the main actual interface for this module
#
def compare_grain(a, b, *options):
    """
    Compare two grains.

    :param a: the first grain
    :param b: the second grain
    :param *options: Additional arguments are options to pass to this comparison. Currently only two types of options are supported:
    options.Exclude.<attribute name> causes the named attribute to be excluded from the comparison. Whereas for integer and timestamp attributes
    it is also possible to use a second type of option: options.ExpectedDifference.<attribute_name> == <value> (or >=, <, <=, >, !=) will set a criteria
    for succesful comparison on that attribute that is less strict that the standard requirement that the values be equal to each other.

    Eg.

    compare(a, b, options.Exclude.data, options.ExpectedDifference.sync_timestamp >= TimeOffset(64, 0))

    will compare the grains, ignoring differences in their data payloads, but requiring that instead of being equal the difference between their sync_timestamps
    must be greater than or equal to 64 seconds.

    :return: an object which is truthy if the comparison matched and falsy if it didn't, in addition the object has a detailed
    human readable summary of the differences between the grains obrainable by calling str on it. In addition any access to an
    attribute of this object that is possessed by grains (eg. .creation_timestamp, .data, .length) will provide another object
    that behaves similarly but represents only that attribute and any attributes/entries it contains. Each such object at any level
    in the tree can be tested as a boolean and can also have .excluded() called on it, which will return True iff the original comparison
    excluded that attribute.

    By default all comparisons ignore differences in creation_timestamp, to force this timestamp to be checked use the options.Include.creation_timestamp
    option.
    """
    return GrainComparisonResult("{}", a, b, options=options)


def compare_grains_pairwise(a, b, *options, return_last_only=False):
    """
    Compare two iterators which produce grains pairwise. Each grain from iterator a will be compared against the corresponding grain in iterator b. The
    comparison will end when any grain fails to match. If one iterator runs out of grains the comparison will end. If both run out at the same time and
    all grains matches then this is considered a succesful match, any other situation is an unsuccessful match.

    :param a: An iterator that generates grains
    :param b: An iterator that generates grains
    :param return_last_only: Set to True to return only the description of the last comparison, instead of all
                             comparisons performed. If False, all compared Grains will be retained, which may require
                             significant memory if the Grain iterators are long.
    :param *options: Additional arguments are passed to the grain comparison mechanism exactly as for compare_grains.

    :returns: An object which will evaluate as True if the iterators matched, and False if they did not. In addition it has a rich description of the
    comparisons performed which is accesstible by calling str on it. A call to first_failing_index() will return the index of the first entry that does not
    match. The object itself is an ordered container containing matcher objects representing the differences between the grains, and these can be accessed
    via the standard [n] index notation, and len() will return the number of such result objects are present.

    By default all comparisons ignore differences in creation_timestamp, to force this timestamp to be checked use the options.Include.creation_timestamp
    option.
    """
    return GrainIteratorComparisonResult("{}", a, b, return_last_only=return_last_only, options=options)
