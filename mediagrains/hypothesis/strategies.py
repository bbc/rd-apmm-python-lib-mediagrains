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
from hypothesis.strategies import integers, from_regex, booleans, uuids, just, tuples, fractions, binary, lists, fixed_dictionaries, one_of, SearchStrategy, builds

from uuid import UUID
from mediatimestamp import Timestamp
from fractions import Fraction
from copy import deepcopy

from .. import Grain, EventGrain


__all__ = ["DONOTSET", "empty_grains", "event_grains", "attributes_for_grain_strategy", "strategy_for_grain_attribute"]


class DONOTSET(object):
    pass


def shrinking_uuids():
    return binary(min_size=16, max_size=16).map(lambda b: UUID(bytes=b))


def fraction_dicts(*args, **kwargs):
    def _fraction_to_dict(f):
        return {'numerator': f.numerator,
                'denominator': f.denominator}
    return builds(_fraction_to_dict, fractions(*args, **kwargs))


def attributes_for_grain_type(grain_type):
    # We don't include length because it's calculated from other things.
    COMMON_ATTRS = ['source_id', 'flow_id', 'origin_timestamp', 'sync_timestamp', 'creation_timestamp', 'rate', 'duration']

    if grain_type == "event":
        return COMMON_ATTRS + ["event_type", "topic", "event_data"]
    else:
        return COMMON_ATTRS


def attributes_for_grain_strategy(strat):
    """Different strategies produce different kinds of grains, this method conveniently helps determine what the writeable attributes
    for the grains from a strategy will be.

    WARNING: Do not pass in a strategy that can generate multiple types of grains. Results are unpredictable.

    :param strat: A strategy that generates a single type of grains
    :returns: A list of strings containing attribute names for the type of grain the strategy generates.
    """
    if strat == event_grains:
        return attributes_for_grain_type("event")
    elif strat == empty_grains:
        return attributes_for_grain_type("empty")
    else:
        return attributes_for_grain_type(strat.example().grain_type)


def strategy_for_grain_attribute(attr):
    """Returns a default strategy for generating data compatible with a particular attribute of a particular grain_type

    :param attr: a string, the name of an attribute of one of the GRAIN subclasses"""

    strats = {'source_id': shrinking_uuids(),
              'flow_id': shrinking_uuids(),
              'origin_timestamp': timestamps(),
              'sync_timestamp': timestamps(),
              'creation_timestamp': timestamps(),
              'rate': fractions(min_value=0),
              'duration': fractions(min_value=0),
              'event_type': from_regex(r"^urn:[a-z0-9][a-z0-9-]{0,31}:[a-z0-9()+,\-.:=@;$_!*'%/?#]+$"),
              'topic': from_regex(r'^[a-zA-Z0-9_\-]+[a-zA-Z0-9_\-/]*$'),
              'event_data': lists(fixed_dictionaries({'path': from_regex(r'^[a-zA-Z0-9_\-]+[a-zA-Z0-9_\-/]*$'),
                                                      'pre': one_of(integers(), booleans(), fraction_dicts(), timestamps().map(str)),
                                                      'post': one_of(integers(), booleans(), fraction_dicts(), timestamps().map(str))}))}
    if attr not in strats:
        raise ValueError("No strategy known for grain attribute: {!r}".format(attr))
    return strats[attr]


def _grain_strategy(builder, grain_type, **kwargs):
    for attr in attributes_for_grain_type(grain_type):
        if attr not in kwargs or kwargs[attr] is None:
            kwargs[attr] = strategy_for_grain_attribute(attr)
        elif kwargs[attr] is DONOTSET:
            kwargs[attr] = just(None)
        else:
            kwargs[attr] = just(kwargs[attr])

    return builds(builder, **kwargs)    


def empty_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET):
    """Draw from this strategy to get empty grains.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on hypothesis.strategies.integers
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

    if rate is DONOTSET:
        rate = Fraction(0, 1)
    if duration is DONOTSET:
        duration = Fraction(0, 1)

    def empty_grain(source_id, flow_id, origin_timestamp, sync_timestamp, rate, duration, creation_timestamp):
        return Grain(src_id=source_id, flow_id=flow_id, creation_timestamp=creation_timestamp, origin_timestamp=origin_timestamp, sync_timestamp=sync_timestamp,
                     rate=rate, duration=duration)

    return _grain_strategy(empty_grain, "empty",
                           source_id=src_id,
                           flow_id=flow_id,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration)


def event_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET,
                 event_type=None,
                 topic=None,
                 event_data=None):
    """Draw from this strategy to get event grains.

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
    :param event_type: a string, a strategy that produces strings, or None. If None then will use
                       hypothesis.strategies.from_regex(r'^urn:[a-z0-9][a-z0-9-]{0,31}:[a-z0-9()+,\-.:=@;$_!*'%/?#]+$')
    :param topic: a string, a strategy that produces strings, or None. If None then will use
                  hypothesis.strategies.from_regex(r'^[a-zA-Z0-9_\-]+[a-zA-Z0-9_\-/]*$')
    :param event_data: a list of dictionaries containing only the keys 'path', 'pre', and 'post', or a strategies that generates them, or None. If None then
                       will use lists(fixed_dictionaries({'path': from_regex(r'^[a-zA-Z0-9_\-]+[a-zA-Z0-9_\-/]*$'),
                                                          'pre': one_of(integers(), booleans(), fraction_dicts(), timestamps()),
                                                          'post': one_of(integers(), booleans(), fraction_dicts(), timestamps())}))
    """
    if rate is DONOTSET:
        rate = Fraction(25, 1)
    if duration is DONOTSET:
        duration = Fraction(1, 25)

    def event_grain(source_id, flow_id, origin_timestamp, sync_timestamp, rate, duration, creation_timestamp, event_type, topic, event_data):
        grain = EventGrain(src_id=source_id, flow_id=flow_id, creation_timestamp=creation_timestamp, origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp, rate=rate, duration=duration,
                           event_type=event_type, topic=topic)
        for datum in event_data:
            grain.append(datum['path'], datum['pre'], datum['post'])
        return grain

    return _grain_strategy(event_grain, "event",
                           source_id=src_id,
                           flow_id=flow_id,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration,
                           creation_timestamp=creation_timestamp,
                           event_type=event_type,
                           topic=topic,
                           event_data=event_data)


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
