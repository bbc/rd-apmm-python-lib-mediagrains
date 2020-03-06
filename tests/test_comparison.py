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

import asynctest as unittest
from asynctest import TestCase

from hypothesis import given, assume, settings, HealthCheck
from hypothesis.strategies import sampled_from, just, tuples, integers
from mediagrains.hypothesis.strategies import grains_with_data, grains

from mediagrains.comparison import compare_grain, compare_grains_pairwise
from mediagrains.comparison.options import Exclude, Include

from mediagrains.grain import attributes_for_grain_type

from copy import deepcopy

from fixtures import pairs_of, attribute_and_pairs_of_grains_of_type_differing_only_in_one_attribute


GRAIN_TYPES_TO_TEST = ["empty", "event", "audio", "video", "coded_audio", "coded_video"]

settings.register_profile("ci", max_examples=1000)
settings.load_profile("ci")


class TestCompareGrain(TestCase):
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains_with_data))
    def test_equal_grains_compare_as_equal(self, a):
        b = deepcopy(a)
        c = compare_grain(a, b, Include.creation_timestamp)
        self.assertTrue(c, msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(a, b, str(c)))
        self.assertEqual(c.failing_attributes(), [])

    @given(pairs_of(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains_with_data)))
    def test_unequal_grains_compare_as_unequal(self, pair):
        (a, b) = pair
        assume(a != b)
        c = compare_grain(a, b, Include.creation_timestamp)
        self.assertFalse(c, msg="Comparison of {!r} and {!r} was equal when inequality was expected:\n\n{}".format(a, b, str(c)))
        self.assertNotEqual(c.failing_attributes(), [])

    # This strategy is complicated and hence quite slow, as a result we turn off the standard timeout deadline for
    # hypothesis tests
    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(attribute_and_pairs_of_grains_of_type_differing_only_in_one_attribute))
    @settings(deadline=None)
    def test_unequal_grains_that_differ_at_specific_points_compare_as_unequal_and_equal_when_difference_is_excluded(self, data_in):
        (excl, (a, b)) = data_in
        assume(getattr(a, excl) != getattr(b, excl))

        # Test unequal
        c = compare_grain(a, b, Include.creation_timestamp)
        self.assertFalse(c, msg="Comparison of {!r} and {!r} was equal when inequality was expected:\n\n{}".format(a, b, str(c)))
        self.assertNotEqual(c.failing_attributes(), [])
        self.assertIn(excl, c.failing_attributes())

        # test equal with exclusions
        c = compare_grain(a, b, Include.creation_timestamp, getattr(Exclude, excl))
        self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertIn(excl, c.failing_attributes())
        self.assertFalse(getattr(c, excl), msg="Expected {!r} to evaluate as false when comparing {!r} and {!r} excluding {}".format(getattr(c, excl),
                                                                                                                                     a,
                                                                                                                                     b,
                                                                                                                                     excl))

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains_with_data).flatmap(lambda g: tuples(just(g),
                                                                                                sampled_from(attributes_for_grain_type(g.grain_type)))))
    def test_equal_grains_compare_as_equal_with_exclusions(self, data_in):
        (a, excl) = data_in
        b = deepcopy(a)
        c = compare_grain(a, b, Include.creation_timestamp, getattr(Exclude, excl))
        self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertEqual(c.failing_attributes(), [])

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(lambda grain_type: tuples(sampled_from(attributes_for_grain_type(grain_type)),
                                                                               just(attributes_for_grain_type(grain_type)),
                                                                               pairs_of(grains_with_data(grain_type)))))
    def test_unequal_grains_compare_as_unequal_with_exclusions_when_difference_is_not_excluded(self, data_in):
        (excl, attrs, (a, b)) = data_in
        assume(any(getattr(a, key) != getattr(b, key) for key in attrs if key != excl))
        c = compare_grain(a, b, Include.creation_timestamp, getattr(Exclude, excl))
        self.assertFalse(c, msg="Comparison of {!r} and {!r} excluding {} was equal when inequality was expected:\n\n{}".format(a, b, excl, str(c)))
        self.assertNotEqual(c.failing_attributes(), [])
        self.assertNotEqual(c.failing_attributes(), [excl])


class TestCompareGrainIterators(TestCase):
    """Test comparing interators of Grains pairwise.

    Note that a maximum of 20 Grains is applied here; there's no significant change to the code path as the number
    of grains increases beyond that point.
    """
    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains), integers(min_value=1, max_value=20))
    def test_pairwise_comparison__equal(self, sample_grain, grain_count):
        a_grains = [sample_grain] * grain_count
        b_grains = deepcopy(a_grains)
        c = compare_grains_pairwise(a_grains, b_grains)
        self.assertTrue(
            c,
            msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(
                a_grains, b_grains, str(c)
            )
        )

        self.assertEqual(len(a_grains), len(c.children))

    @given(pairs_of(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains)), integers(min_value=0, max_value=19))
    def test_pairwise_comparison__unequal(self, pair, difference_index):
        (a, b) = pair
        assume(a != b)

        a_grains = [a] * 20
        b_grains = deepcopy(a_grains)
        b_grains[difference_index] = b

        c = compare_grains_pairwise(a_grains, b_grains, Include.creation_timestamp)
        self.assertFalse(
            c,
            msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(
                a_grains, b_grains, str(c)
            )
        )

        self.assertEqual(difference_index + 1, len(c.children))

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains),
           integers(min_value=1, max_value=20), integers(min_value=1, max_value=20))
    def test_pairwise_comparison__different_length_unequal(self, sample_grain, grain_count_a, grain_count_b):
        """Test that pairwise comparison doesn't match if the grain iterators have different lengths"""
        assume(grain_count_a != grain_count_b)

        a_grains = [sample_grain] * grain_count_a
        b_grains = [sample_grain] * grain_count_b

        c = compare_grains_pairwise(a_grains, b_grains, Include.creation_timestamp)
        self.assertFalse(
            c,
            msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(
                a_grains, b_grains, str(c)
            )
        )

    @given(sampled_from(GRAIN_TYPES_TO_TEST).flatmap(grains), integers(min_value=1, max_value=20))
    def test_pairwise_comparison__return_last_only(self, sample_grain, grain_count):
        a_grains = [sample_grain] * grain_count
        b_grains = deepcopy(a_grains)
        c = compare_grains_pairwise(a_grains, b_grains, return_last_only=True)
        self.assertTrue(
            c,
            msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(
                a_grains, b_grains, str(c)
            )
        )

        self.assertEqual(1, len(c.children))

    def test_pairwise_comparison__empty_iterator(self):
        """Test that comparing two empty iterators pairwise returns True, but no children"""
        c = compare_grains_pairwise([], [])
        self.assertTrue(
            c,
            msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format([], [], str(c))
        )

        self.assertEqual(0, len(c.children))


if __name__ == "__main__":
    unittest.main()
