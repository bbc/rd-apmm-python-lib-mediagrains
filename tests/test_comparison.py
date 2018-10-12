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

from __future__ import print_function
from __future__ import absolute_import

import unittest
from cloudfit_fixtures import APMMTestCase

from hypothesis import given, assume, reproduce_failure, seed, settings, HealthCheck
from hypothesis.strategies import uuids, from_regex, one_of, lists, builds, sampled_from, just, tuples
from mediagrains.hypothesis.strategies import grains, empty_grains, event_grains, audio_grains, grains_varying_entries, attributes_for_grain_type, strategy_for_grain_attribute
from mediatimestamp.hypothesis.strategies import timestamps

from mediatimestamp import Timestamp

from mediagrains.comparison import compare_grain, Exclude

from copy import deepcopy


def pairs_of(strategy):
    return lists(strategy, min_size=2, max_size=2).map(tuple)


def pairs_of_grains_of_type_differing_only_at_specified_attribute(grain_type, attr):
    """Strategy giving pairs of grains of the specified type that differ from each other only in the specified attribute"""
    return grains_varying_entries(grains(grain_type), {attr: strategy_for_grain_attribute(attr, grain_type=grain_type)}, max_size=2).map(tuple)


def attribute_and_pairs_of_grains_of_type_differing_only_in_one_attribute(grain_type):
    """Strategy giving a tuple of an attribute name and a pair of grains of the specified type that differ only in the drawn attribute"""
    return sampled_from(attributes_for_grain_type(grain_type)).flatmap(lambda attr: tuples(just(attr),
                                                                                           pairs_of_grains_of_type_differing_only_at_specified_attribute(grain_type, attr)))


GRAIN_TYPES_TO_TEST = ["empty", "event", "audio"]

settings.register_profile("ci", max_examples=1000)
settings.load_profile("ci")


class TestCompareGrain(APMMTestCase):
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains))
    def test_equal_grains_compare_as_equal(self, a):
        b = deepcopy(a)
        c = compare_grain(a, b)
        self.assertTrue(c, msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(a, b, str(c)))
        self.assertEqual(c.failing_attributes(), [])

    @given(pairs_of(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains)))
    def test_unequal_grains_compare_as_unequal(self, pair):
        (a, b) = pair
        assume(a != b)
        c = compare_grain(a, b)
        self.assertFalse(c, msg="Comparison of {!r} and {!r} was equal when inequality was expected:\n\n{}".format(a, b, str(c)))
        self.assertNotEqual(c.failing_attributes(), [])

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(attribute_and_pairs_of_grains_of_type_differing_only_in_one_attribute))
    def test_unequal_grains_compare_as_equal_with_exclusions_when_difference_is_excluded(self, data_in):
        (excl, (a, b)) = data_in
        assume(getattr(a, excl) != getattr(b, excl))
        c = compare_grain(a, b, getattr(Exclude, excl))
        self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertIn(excl, c.failing_attributes())
        self.assertFalse(getattr(c, excl), msg="Expected {!r} to evaluate as false when comparing {!r} and {!r} excluding {}".format(getattr(c, excl), a, b, excl))

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains).flatmap(lambda g: tuples(just(g), sampled_from(attributes_for_grain_type(g.grain_type)))))
    def test_equal_grains_compare_as_equal_with_exclusions(self, data_in):
        (a, excl) = data_in
        b = deepcopy(a)
        c = compare_grain(a, b, getattr(Exclude, excl))
        self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertEqual(c.failing_attributes(), [])

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(lambda grain_type: tuples(sampled_from(attributes_for_grain_type(grain_type)),
                                                                               just(attributes_for_grain_type(grain_type)),
                                                                               pairs_of(grains(grain_type)))))
    def test_unequal_grains_compare_as_unequal_with_exclusions_when_difference_is_not_excluded(self, data_in):
        (excl, attrs, (a, b)) = data_in
        assume(any(getattr(a, key) != getattr(b, key) for key in attrs if key != excl))
        c = compare_grain(a, b, getattr(Exclude, excl))
        self.assertFalse(c, msg="Comparison of {!r} and {!r} excluding {} was equal when inequality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertNotEqual(c.failing_attributes(), [])
        self.assertNotEqual(c.failing_attributes(), [excl])


if __name__ == "__main__":
    unittest.main()
