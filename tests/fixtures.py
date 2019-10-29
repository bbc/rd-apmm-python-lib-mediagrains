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

from hypothesis.strategies import lists, sampled_from, just, tuples, fixed_dictionaries
from mediagrains.hypothesis.strategies import grains, strategy_for_grain_attribute, grains_from_template_with_data

from mediagrains.grain import attributes_for_grain_type

from copy import deepcopy

import asyncio
import warnings

from functools import wraps


def pairs_of(strategy):
    return lists(strategy, min_size=2, max_size=2).map(tuple)


def lists_of_grains_varying_entries(grains, entry_strategies, min_size=2, max_size=None):
    def _grain_adjusting_entries(grain, entries):
        g = deepcopy(grain)
        for key in entries:
            setattr(g, key, entries[key])
        return g

    return grains.flatmap(lambda grain: lists(fixed_dictionaries(entry_strategies),
                                              min_size=min_size,
                                              max_size=max_size).map(lambda dicts: [_grain_adjusting_entries(grain, entries) for entries in dicts]))


def pairs_of_grains_of_type_differing_only_at_specified_attribute(grain_type, attr):
    """Strategy giving pairs of grains of the specified type that differ from each other only in the specified attribute"""
    return lists_of_grains_varying_entries(grains(grain_type), {attr: strategy_for_grain_attribute(attr, grain_type=grain_type)}, max_size=2).map(tuple)


def attribute_and_pairs_of_grains_of_type_differing_only_in_one_attribute(grain_type):
    """Strategy giving a tuple of an attribute name and a pair of grains of the specified type that differ only in the drawn attribute.

    For some types of grain the attribute drawn can include "data" which is generated a little differently from other types of attribute as befits its unusual
    nature"""

    attr_strat = attributes_for_grain_type(grain_type)
    grain_strat = sampled_from(attr_strat).flatmap(lambda attr: tuples(just(attr),
                                                                       pairs_of_grains_of_type_differing_only_at_specified_attribute(grain_type, attr)))

    if grain_type in ("audio", "video", "coded_audio", "coded_video"):
        return grain_strat | grains(grain_type).flatmap(lambda g: tuples(just("data"), pairs_of(grains_from_template_with_data(g))))
    else:
        return grain_strat


def suppress_deprecation_warnings(f):
    @wraps(f)
    def __inner(*args, **kwargs):
        with warnings.catch_warnings(record=True) as warns:
            r = f(*args, **kwargs)

        for w in warns:
            if w.category != DeprecationWarning:
                warnings.showwarning(w.message, w.category, w.filename, w.lineno)

        return r


def async_test(suppress_warnings):
    def __outer(f):
        @wraps(f)
        def __inner(*args, **kwargs):
            loop = asyncio.get_event_loop()
            loop.set_debug(True)
            E = None
            warns = []

            try:
                with warnings.catch_warnings(record=True) as warns:
                    loop.run_until_complete(f(*args, **kwargs))

            except AssertionError as e:
                E = e
            except Exception as e:
                E = e

            runtime_warnings = [w for w in warns if w.category == RuntimeWarning]

            for w in (runtime_warnings if suppress_warnings else warns):
                warnings.showwarning(w.message,
                                     w.category,
                                     w.filename,
                                     w.lineno)
            if E is None:
                args[0].assertEqual(len(runtime_warnings), 0,
                                    msg="asyncio subsystem generated warnings due to unawaited coroutines")
            else:
                raise E

        return __inner

    if callable(suppress_warnings):
        # supress_warnings is actually f
        f = suppress_warnings
        suppress_warnings = False
        return __outer(f)
    else:
        return __outer
