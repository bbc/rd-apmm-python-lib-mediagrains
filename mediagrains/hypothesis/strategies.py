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

from mediatimestamp.hypothesis.strategies import immutabletimestamps as timestamps
from hypothesis.strategies import (
    integers,
    from_regex,
    booleans,
    just,
    fractions,
    binary,
    lists,
    fixed_dictionaries,
    one_of,
    SearchStrategy,
    builds,
    sampled_from,
    floats
)

import struct

from uuid import UUID
from fractions import Fraction
from copy import copy

from ..grain import attributes_for_grain_type
from ..cogenums import CogAudioFormat, CogFrameFormat, CogFrameLayout
from .. import Grain, EventGrain, AudioGrain, CodedAudioGrain, CodedVideoGrain, VideoGrain


__all__ = ["DONOTSET",
           "empty_grains",
           "event_grains",
           "audio_grains",
           "video_grains",
           "coded_audio_grains",
           "coded_video_grains",
           "grains",
           "grains_from_template_with_data",
           "strategy_for_grain_attribute",
           "shrinking_uuids",
           "fraction_dicts",
           "grains_with_data"]


DONOTSET = object()


def shrinking_uuids():
    """A strategy that produces uuids, but shrinks towards 0, unlike the standard hypothesis one."""
    return binary(min_size=16, max_size=16).map(lambda b: UUID(bytes=b))


def fraction_dicts(*args, **kwargs):
    """A strategy that produces dictionaries of the form {'numerator': n, 'denominator': d} for fractions generated using the fractions strategy.
    All arguments are passed through to the underlying call to fractions."""
    def _fraction_to_dict(f):
        return {'numerator': f.numerator,
                'denominator': f.denominator}
    return builds(_fraction_to_dict, fractions(*args, **kwargs))


def strategy_for_grain_attribute(attr, grain_type=None):
    """Returns a default strategy for generating data compatible with a particular attribute of a particular grain_type

    :param attr: a string, the name of an attribute of one of the GRAIN subclasses
    :param grain_type: some grains types have attributes of the same name, but which require different strategies
    :returns: a strategy."""

    def _format_strategy(grain_type):
        if grain_type == "audio":
            # Uncompressed audio formats
            return sampled_from(CogAudioFormat).filter(lambda x: x < 0x200)
        elif grain_type == "coded_audio":
            return sampled_from(CogAudioFormat).filter(lambda x: (x & 0x200) != 0 and x != CogAudioFormat.INVALID)
        elif grain_type == "video":
            return sampled_from(CogFrameFormat).filter(lambda x: ((x >> 9) & 0x1) == 0)
        elif grain_type == "coded_video":
            return sampled_from(CogFrameFormat).filter(lambda x: (x & 0x200) != 0 and x != CogFrameFormat.INVALID)
        else:
            return ValueError("Cannot generate formats for grain type: {!r}".format(grain_type))

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
                                                      'post': one_of(integers(), booleans(), fraction_dicts(), timestamps().map(str))})),
              'format': _format_strategy(grain_type),
              'samples': integers(min_value=1, max_value=16),
              'channels': integers(min_value=1, max_value=16),
              'sample_rate': sampled_from((48000, 44100)),
              'width': just(240),
              'height': just(135),
              'layout': sampled_from(CogFrameLayout).filter(lambda x: x != CogFrameLayout.UNKNOWN),
              'priming': integers(min_value=0, max_value=65535),
              'remainder': integers(min_value=0, max_value=256),
              'coded_width': just(240),
              'coded_height': just(135),
              'origin_width': just(240),
              'origin_height': just(135),
              'is_key_frame': booleans(),
              'temporal_offset': integers(min_value=0, max_value=16),
              'unit_offsets': just(None) | lists(integers(min_value=0, max_value=256), min_size=0, max_size=16).filter(sorted)}
    if attr not in strats:
        raise ValueError("No strategy known for grain attribute: {!r}".format(attr))
    if isinstance(strats[attr], Exception):
        raise strats[attr]
    return strats[attr]


def _grain_strategy(builder, grain_type, **kwargs):
    new_kwargs = {}
    for attr in attributes_for_grain_type(grain_type):
        if attr not in kwargs or kwargs[attr] is None:
            new_kwargs[attr] = strategy_for_grain_attribute(attr, grain_type=grain_type)
        elif kwargs[attr] is DONOTSET:
            pass
        elif isinstance(kwargs[attr], SearchStrategy):
            new_kwargs[attr] = kwargs[attr]
        else:
            new_kwargs[attr] = just(kwargs[attr])

    return builds(builder, **new_kwargs)


def empty_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET):
    """Draw from this strategy to get empty grains.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on
                      hypothesis.strategies.integers which shrinks towards smaller numerical values will be used.
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
    return _grain_strategy(Grain, "empty",
                           source_id=src_id,
                           flow_id=flow_id,
                           creation_timestamp=creation_timestamp,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration)


def audio_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET,
                 format=None,
                 samples=None,
                 channels=None,
                 sample_rate=None):
    """Draw from this strategy to get audio grains. The data element of these grains will always be all 0s.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on
                      hypothesis.strategies.integers which shrinks towards smaller numerical values will be used.
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
    :param format: either a member of cogenums.CogAudioFormat or a strategy that generates them. The default strategy will not produce encoded or unknown
                   formats.
    :param samples: either a positive integer or a strategy that generates them, the default strategy is integers(min_value=1).
    :param channels: either a positive integer or a strategy that generates them, the default strategy is integers(min_value=1).
    :param sample_rate: either a positive integer or a strategy that generates them, the default strategy will always generate either 48000 or 44100.
    """
    return _grain_strategy(AudioGrain, "audio",
                           source_id=src_id,
                           flow_id=flow_id,
                           creation_timestamp=creation_timestamp,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration,
                           format=format,
                           samples=samples,
                           channels=channels,
                           sample_rate=sample_rate)


def coded_audio_grains(src_id=None,
                       flow_id=None,
                       creation_timestamp=None,
                       origin_timestamp=None,
                       sync_timestamp=None,
                       rate=DONOTSET,
                       duration=DONOTSET,
                       format=None,
                       samples=None,
                       channels=None,
                       priming=DONOTSET,
                       remainder=DONOTSET,
                       sample_rate=None):
    """Draw from this strategy to get coded audio grains. The data element of these grains will always be all 0s.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on
                      hypothesis.strategies.integers which shrinks towards smaller numerical values will be used.
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
    :param format: either a member of cogenums.CogAudioFormat or a strategy that generates them. The default strategy will not produce encoded or unknown
                   formats.
    :param samples: either a positive integer or a strategy that generates them, the default strategy is integers(min_value=1).
    :param channels: either a positive integer or a strategy that generates them, the default strategy is integers(min_value=1).
    :param priming: either a positive integer or a strategy that generates them, by default this value is left unset, and so defaults to 0 on all generated
                    grains
    :param remainder: either a positive integer or a strategy that generates them, by default this value is left unset, and so defaults to 0 on all generated
                      grains
    :param sample_rate: either a positive integer or a strategy that generates them, the default strategy will always generate either 48000 or 44100.
    """
    return _grain_strategy(CodedAudioGrain, "coded_audio",
                           source_id=src_id,
                           flow_id=flow_id,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration,
                           format=format,
                           samples=samples,
                           channels=channels,
                           sample_rate=sample_rate,
                           priming=priming,
                           remainder=remainder)


def video_grains(src_id=None,
                 flow_id=None,
                 creation_timestamp=None,
                 origin_timestamp=None,
                 sync_timestamp=None,
                 rate=DONOTSET,
                 duration=DONOTSET,
                 format=None,
                 width=None,
                 height=None,
                 layout=None):
    """Draw from this strategy to get video grains. The data element of these grains will always be all 0s.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on
                      hypothesis.strategies.integers which shrinks towards smaller numerical values will be used.
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
    :param format: either a member of cogenums.CogFrameFormat or a strategy that generates them. The default strategy will not produce encoded or unknown
                   formats.
    :param width: either a positive integer or a strategy that generates them, the default strategy is just(240).
    :param height: either a positive integer or a strategy that generates them, the default strategy is just(135).
    :param layout: either a member of cogenums.CogFrameLayout or a strategy that generates them, the default strategy will not generate UNKNOWN layout.
    """
    return _grain_strategy(VideoGrain, "video",
                           source_id=src_id,
                           flow_id=flow_id,
                           creation_timestamp=creation_timestamp,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration,
                           format=format,
                           width=width,
                           height=height,
                           layout=layout)


def coded_video_grains(src_id=None,
                       flow_id=None,
                       creation_timestamp=None,
                       origin_timestamp=None,
                       sync_timestamp=None,
                       rate=DONOTSET,
                       duration=DONOTSET,
                       format=None,
                       coded_width=None,
                       coded_height=None,
                       layout=None,
                       origin_width=None,
                       origin_height=None,
                       is_key_frame=None,
                       temporal_offset=None,
                       unit_offsets=None):
    """Draw from this strategy to get coded video grains. The data element of these grains will always be all 0s.

    :param source_id: A uuid.UUID *or* a strategy from which uuid.UUIDs can be drawn, if None is provided then an strategy based on
                      hypothesis.strategies.integers which shrinks towards smaller numerical values will be used.
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
    :param format: either a member of cogenums.CogFrameFormat or a strategy that generates them. The default strategy will not produce encoded or unknown
                   formats.
    :param coded_width: either a positive integer or a strategy that generates them, the default strategy is just(240).
    :param coded_height: either a positive integer or a strategy that generates them, the default strategy is just(135).
    :param origin_width: either a positive integer or a strategy that generates them, the default strategy is just(240).
    :param origin_height: either a positive integer or a strategy that generates them, the default strategy is just(135).
    :param is_key_frame: either a boolean or a strategy that generates them.
    :param temporal_offset: either an integer or a strategy that generates them.
    :param unit_offsets: either a list of uniformly increasing non-negative integers or a strategy that generates them.
    :param layout: either a member of cogenums.CogFrameLayout or a strategy that generates them, the default strategy will not generate UNKNOWN layout.
    """
    return _grain_strategy(CodedVideoGrain, "coded_video",
                           source_id=src_id,
                           flow_id=flow_id,
                           creation_timestamp=creation_timestamp,
                           origin_timestamp=origin_timestamp,
                           sync_timestamp=sync_timestamp,
                           rate=rate,
                           duration=duration,
                           format=format,
                           origin_width=origin_width,
                           origin_height=origin_height,
                           coded_width=coded_width,
                           coded_height=coded_height,
                           is_key_frame=is_key_frame,
                           temporal_offset=temporal_offset,
                           unit_offsets=unit_offsets,
                           layout=layout)


def grains(grain_type, **kwargs):
    """A strategy that generates grains of the specified type."""

    if grain_type == "empty":
        return empty_grains(**kwargs)
    elif grain_type == "audio":
        return audio_grains(**kwargs)
    elif grain_type == "coded_audio":
        return coded_audio_grains(**kwargs)
    elif grain_type == "event":
        return event_grains(**kwargs)
    elif grain_type == "video":
        return video_grains(**kwargs)
    elif grain_type == "coded_video":
        return coded_video_grains(**kwargs)

    raise ValueError("Cannot find a strategy to generate grains of type: {}".format(grain_type))


def grains_with_data(grain_type):
    """Strategy giving grains which have data payloads filled out using an appropriate strategy for the grain type.

    :param grain_type: The type of grains to generate"""
    if grain_type in ("audio", "video", "coded_audio", "coded_video"):
        return grains(grain_type).flatmap(lambda g: grains_from_template_with_data(g))
    else:
        return grains(grain_type)


def grains_from_template_with_data(grain, data=None):
    """A strategy that produces grains which are identical to the input grain but with randomised data based on the format:

    :param grain: A grain to use as a template
    :param data: either a strategy that generates bytes of the correct size, or a bytestring of the right size, or None, in which case random data based on the
                 format will be used.
    """
    if data is None:
        if grain.grain_type == "audio":
            if grain.format in [CogAudioFormat.FLOAT_PLANES,
                                CogAudioFormat.FLOAT_PAIRS,
                                CogAudioFormat.FLOAT_INTERLEAVED]:
                ln = grain.expected_length//4
                data = lists(floats(width=32,
                                    allow_nan=False,
                                    allow_infinity=False),
                             min_size=ln,
                             max_size=ln).map(lambda x: struct.pack('@' + ('f'*ln), *x))
            elif grain.format in [CogAudioFormat.DOUBLE_PLANES,
                                  CogAudioFormat.DOUBLE_PAIRS,
                                  CogAudioFormat.DOUBLE_INTERLEAVED]:
                ln = grain.expected_length//8
                data = lists(floats(width=64,
                                    allow_nan=False,
                                    allow_infinity=False),
                             min_size=ln,
                             max_size=ln).map(lambda x: struct.pack('@' + ('d'*ln), *x))
            else:
                data = binary(min_size=grain.expected_length, max_size=grain.expected_length)
        else:
            data = binary(min_size=grain.length, max_size=grain.length)

    elif not isinstance(data, SearchStrategy):
        data = just(data)

    def grain_with_data(grain, data):
        grain = copy(grain)
        grain.data = data
        return grain

    return builds(grain_with_data, just(grain), data)


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
    """  # noqa W605 Ignore invalid escape sequence in docstring
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
