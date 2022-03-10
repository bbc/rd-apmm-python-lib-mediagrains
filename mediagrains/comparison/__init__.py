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
The submodule which gives nuanced grain comparison capabilities.
"""

from ._internal import GrainComparisonResult, GrainIteratorComparisonResult
from .psnr import compute_psnr

__all__ = ["compare_grain", "compare_grains_pairwise", "compute_psnr"]


#
# The compare_grain method is the main actual interface for this module
#
def compare_grain(a, b, *options) -> GrainComparisonResult:
    """
    Compare two grains.

    :param a: the first grain
    :param b: the second grain
    :param *options: Additional arguments are options to pass to this comparison. See options.py for available options
    :return: GrainComparisonResult

    By default all comparisons ignore differences in creation_timestamp, to force this timestamp to be checked use the
    options.Include.creation_timestamp option.
    """
    return GrainComparisonResult("{}", a, b, options=options)


def compare_grains_pairwise(a, b, *options, return_last_only=False) -> GrainIteratorComparisonResult:
    """
    Compare two iterators that create grains, pairwise.

    :param a: An iterator that generates grains
    :param b: An iterator that generates grains
    :param return_last_only: Set to True to return only the description of the last comparison, lowers memory usage.
    :param *options: Additional arguments are passed to the grain comparison mechanism exactly as for compare_grains.

    :returns: GrainIteratorComparisonResult

    By default all comparisons ignore differences in creation_timestamp, to force this timestamp to be checked use the
    options.Include.creation_timestamp option.
    """
    return GrainIteratorComparisonResult("{}", a, b, return_last_only=return_last_only, options=options)
