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

from hypothesis import given, assume
from hypothesis.strategies import uuids
from mediagrains.hypothesis.strategies import empty_grains, grains_varying_entries
from mediatimestamp.hypothesis.strategies import timestamps

from mediatimestamp import Timestamp

from mediagrains.comparison import compare_grain, Exclude

from copy import deepcopy


class TestCompareGrain(APMMTestCase):
    @given(empty_grains())
    def test_empty_grains_equal(self, a):
        b = deepcopy(a)
        c = compare_grain(a, b)
        self.assertTrue(c, msg="Comparison of {!r} and {!r} was unequal when equality was expected:\n\n{}".format(a, b, str(c)))

    @given(empty_grains(),
           empty_grains())
    def test_empty_grains_unequal(self, a, b):
        assume(not ((a.source_id == b.source_id) and
                    (a.flow_id == b.flow_id) and
                    (a.origin_timestamp == b.origin_timestamp) and
                    (a.sync_timestamp == b.sync_timestamp) and
                    (a.creation_timestamp == b.creation_timestamp)))
        c = compare_grain(a, b)
        self.assertFalse(c, msg="Comparison of {!r} and {!r} was equal when inequality was expected:\n\n{}".format(a, b, str(c)))

    def test_empty_grains_compare_as_equal_with_exclusions_when_not_actually_equal(self):
        def _check(self, excl, grains):
            (a, b) = grains
            assume(getattr(a, excl) != getattr(b, excl))
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))

        for excl in ['source_id',
                     'flow_id']:
            given(grains_varying_entries(empty_grains(), {excl: uuids()}, max_size=2))(_check)(self, excl)

        for excl in ['origin_timestamp',
                     'sync_timestamp',
                     'creation_timestamp']:
            given(grains_varying_entries(empty_grains(), {excl: timestamps()}, max_size=2))(_check)(self, excl)

    @given(empty_grains())
    def test_empty_grains_equal_with_exclusions(self, a):
        b = deepcopy(a)
        for excl in ['source_id',
                     'flow_id',
                     'origin_timestamp',
                     'sync_timestamp',
                     'creation_timestamp']:
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertTrue(c, msg="Comparison of {!r} and {!r} excluding {} was unequal when equality was expected:\n\n{}".format(a, b, excl, str(c)))

    def test_empty_grains_unequal_with_exclusions_if_inequality_outside_exclusions(self):
        @given(empty_grains(), empty_grains())
        def _check(self, excl, a, b):
            assume(any(getattr(a, key) != getattr(b, key) for key in ['source_id',
                                                                      'flow_id',
                                                                      'origin_timestamp',
                                                                      'sync_timestamp',
                                                                      'creation_timestamp'] if key != excl))
            c = compare_grain(a, b, getattr(Exclude, excl))
            self.assertFalse(c, msg="Comparison of {!r} and {!r} excluding {} was equal when inequality was expected:\n\n{}".format(a, b, excl, str(c)))

        for excl in ['source_id',
                     'flow_id',
                     'origin_timestamp',
                     'sync_timestamp',
                     'creation_timestamp']:
            _check(self, excl)
