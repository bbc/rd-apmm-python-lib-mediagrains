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
Contains a number of useful hypothesis strategies which can be used to
generate mediagrains for hypothesis based testing
"""

from __future__ import print_function
from __future__ import absolute_import

from mediatimestamp.hypothesis.strategies import timestamps
from hypothesis.strategies import uuids, just, tuples, fractions, binary, lists, fixed_dictionaries, SearchStrategy

from uuid import UUID
from mediatimestamp import Timestamp
from fractions import Fraction
from copy import deepcopy

from .. import Grain


__all__ = ["DONOTSET", "empty_grains"]


class DONOTSET(object):
    pass


def shrinking_uuids():
    return binary(min_size=16, max_size=16).map(lambda b: UUID(bytes=b))


def empty_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET):
    """Draw from this strategy to get empty grains.

    :param src_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on hypothesis.strategies.integers
                   which shrinks towards smaller numerical values will be used.
    :param flow_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then based on hypothesis.strategies.integers which
                    shrinks towards smaller numerical values will be used.
    :param creation_timestamp: a mediagrains.Timestamp *or* a strategy from which mediagrain.Timestamps can be drawn, if None is provided then
                               mediagrains.hypothesis.strategies.timestamps will be used (the default), if DONOTSET is passed then the creation_timestamp will
                               be the time when drawing occured (this is unlikely to be what you want).
    :param origin_timestamp: a mediagrains.Timestamp *or* a strategy from which mediagrain.Timestamps can be drawn, if None is provided then
                             mediagrains.hypothesis.strategies.timestamps will be used  (the default), if DONOTSET is passed then the origin_timestamp of each
                             grain drawn will be set to be equal to the creation_timestamp.
    :param sync_timestamp: a mediagrains.Timestamp *or* a strategy from which mediagrain.Timestamps can be drawn, if None is provided then
                           mediagrains.hypothesis.strategies.timestamps will be used (the default), if DONOTSET is passed then the sync_timestamp will be set
                           equal to the origin_timestamp on all drawn grains.
    :param rate: something that can be passed to the constructor of fractions.Fraction or a strategy that generates them, or the value DONOTSET (the default)
                 which causes the default rate to be used for all grains, or the value None in which case hypothesis.strategies.fractions will be used with
                 min_value set to 0.
    :param duration: something that can be passed to the constructor of fractions.Fraction or a strategy that generates them, or the value DONOTSET (the
                     default) which causes the default rate to be used for all grains, or the value None in which case hypothesis.strategies.fractions will be
                     used with min_value set to 0.
    """

    if src_id is None:
        src_id = shrinking_uuids()
    elif isinstance(src_id, UUID):
        src_id = just(src_id)

    if flow_id is None:
        flow_id = shrinking_uuids()
    elif isinstance(flow_id, UUID):
        flow_id = just(flow_id)

    if origin_timestamp is None:
        origin_timestamp = timestamps()
    elif origin_timestamp is DONOTSET:
        origin_timestamp = just(None)
    elif isinstance(origin_timestamp, Timestamp):
        origin_timestamp = just(origin_timestamp)

    if sync_timestamp is None:
        sync_timestamp = timestamps()
    elif sync_timestamp is DONOTSET:
        sync_timestamp = just(None)
    elif isinstance(sync_timestamp, Timestamp):
        sync_timestamp = just(sync_timestamp)

    if creation_timestamp is None:
        creation_timestamp = timestamps()
    elif creation_timestamp is DONOTSET:
        creation_timestamp = just(None)
    elif isinstance(creation_timestamp, Timestamp):
        creation_timestamp = just(creation_timestamp)

    if rate is None:
        rate = fractions(min_value=0)
    elif rate is DONOTSET:
        rate = just(Fraction(0, 1))
    elif not isinstance(rate, SearchStrategy):
        rate = just(rate)

    if duration is None:
        duration = fractions(min_value=0)
    elif duration is DONOTSET:
        duration = just(Fraction(0, 1))
    elif not isinstance(duration, SearchStrategy):
        duration = just(duration)

    def empty_grain(src_id, flow_id, origin_timestamp, sync_timestamp, rate, duration, creation_timestamp):
        return Grain(src_id=src_id, flow_id=flow_id, creation_timestamp=creation_timestamp, origin_timestamp=origin_timestamp, sync_timestamp=sync_timestamp,
                     rate=rate, duration=duration)

    return tuples(src_id, flow_id, origin_timestamp, sync_timestamp, rate, duration, creation_timestamp).map(lambda args: empty_grain(*args))


def grains_varying_entries(grains, entry_strategies, min_size=2, average_size=None, max_size=None):
    """A strategy which generates a list of grains that differ only in the specified features.

    :param grains: a strategy that produces grains to use as the initial template
    :param entry_strategies: a dictionary mapping grain attribute names to strategies for generating them
    :param min_size: The minimum size of the generated list (default is 2)
    :param average_size: The average size of the generated list (default is None)
    :param max_size: The max size of the generated list (default is None)
    """

    def grain_adjusting_entries(grain, entries):
        g = deepcopy(grain)
        for key in entries:
            setattr(g, key, entries[key])
        return g

    return grains.flatmap(lambda grain: lists(fixed_dictionaries(entry_strategies),
                                              min_size=min_size,
                                              average_size=average_size,
                                              max_size=max_size).map(lambda dicts: [grain_adjusting_entries(grain, entries) for entries in dicts]))
