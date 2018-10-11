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

from cloudfit_fixtures import APMMTestCase

from hypothesis import given, assume, reproduce_failure
from hypothesis.strategies import uuids, from_regex
from mediagrains.hypothesis.strategies import empty_grains, event_grains, grains_varying_entries, attributes_for_grain_strategy, strategy_for_grain_attribute
from mediatimestamp.hypothesis.strategies import timestamps

from mediatimestamp import Timestamp

from mediagrains.comparison import compare_grain, Exclude

from copy import deepcopy


class TestCompareGrain(APMMTestCase):
    def test_equal_grains_compare_as_equal(self):
        def _check(self, a):
            b = deepcopy(a)
            c = compare_grain(a, b)
            self.assertTrue(c, msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(a, b, str(c)))
            self.assertEqual(c.failing_attributes(), [])

        for grains in [empty_grains, event_grains]:
            given(grains())(_check)(self)

    def test_unequal_grains_compare_as_unequal(self):
        def _check(self, a, b):
            assume(a != b)
            c = compare_grain(a, b)
            self.assertFalse(c, msg="Comparison of {!r} and {!r} was equal when inequality was expected:\n\n{}".format(a, b, str(c)))
            self.assertNotEqual(c.failing_attributes(), [])

        for grains in [empty_grains, event_grains]:
            given(grains(), grains())(_check)(self)

    def test_unequal_grains_compare_as_equal_with_exclusions_when_difference_is_excluded(self):
        def _check(self, excl, grains):
            (a, b) = grains
            assume(getattr(a, excl) != getattr(b, excl))
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
            self.assertIn(excl, c.failing_attributes())
            self.assertFalse(getattr(c, excl), msg="Expected {!r} to evaluate as false when comparing {!r} and {!r} excluding {}".format(getattr(c, excl), a, b, excl))

        for grains in [empty_grains, event_grains]:
            for excl in attributes_for_grain_strategy(grains):
                given(grains_varying_entries(grains(), {excl: strategy_for_grain_attribute(excl)}, max_size=2))(_check)(self, excl)

    def test_equal_grains_compare_as_equal_with_exclusions(self):
        def _check(self, excl, a):
            b = deepcopy(a)
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))
            self.assertEqual(c.failing_attributes(), [])

        for grains in [empty_grains, event_grains]:
            for excl in attributes_for_grain_strategy(grains):
                given(grains())(_check)(self, excl)

    def test_unequal_grains_compare_as_unequal_with_exclusions_when_difference_is_not_excluded(self):
        def _check(self, excl, attrs, a, b):
            assume(any(getattr(a, key) != getattr(b, key) for key in attrs if key != excl))
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertFalse(c, msg="Comparison of {!r} and {!r} excluding {} was equal when inequality was expected:\n\n{}".format(a, b, excl, str(c)))
            self.assertNotEqual(c.failing_attributes(), [])
            self.assertNotEqual(c.failing_attributes(), [excl])

        for grains in [empty_grains, event_grains]:
            attrs = attributes_for_grain_strategy(grains)
            for excl in attrs:
                given(grains(), grains())(_check)(self, excl, attrs)
