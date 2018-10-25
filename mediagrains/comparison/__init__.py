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

from __future__ import print_function
from __future__ import absolute_import

from ._internal import GrainComparisonResult

__all__ = ["compare_grain"]


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
    """
    return GrainComparisonResult(a, b, options=options)
