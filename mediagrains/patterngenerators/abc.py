#
# Copyright 2020 British Broadcasting Corporation
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
from typing import TypeVar, Generic, Union, overload, Iterator, Optional
from abc import ABCMeta, abstractmethod
from fractions import Fraction
import itertools

from mediatimestamp import (
    TimeOffset,
    Timestamp,
    TimeValueRange,
    RangeTypes,
    TimeValue,
    TimeValueConstructTypes,
    RangeConstructionTypes,
    SupportsMediaTimeOffset,
    SupportsMediaTimestamp,
    TimeRange,
    CountRange,
    SupportsMediaTimeRange)

from ..grain import GRAIN


__all__ = ["PatternGenerator", "FixedRatePatternGenerator"]


G = TypeVar('G', bound=GRAIN)


class PatternGenerator (Generic[G], metaclass=ABCMeta):
    def __init__(self):
        pass

    @overload
    def __getitem__(self, key: Union[slice]) -> Iterator[G]: ...

    @overload
    def __getitem__(self, key: Union[RangeTypes]) -> Iterator[G]: ...

    @overload
    def __getitem__(self, key: TimeValueConstructTypes) -> G: ...

    @overload
    def __getitem__(self, key: RangeConstructionTypes) -> Union[G, Iterator[G]]: ...

    def __getitem__(self, key):
        rng: Optional[TimeValueRange] = None
        val: Optional[TimeValue] = None
        skip: int = 1

        if isinstance(key, slice):
            start: Optional[TimeValue] = None
            stop: Optional[TimeValue] = None
            rate: Optional[Fraction] = None

            if key.start is not None:
                start = TimeValue(key.start)
            if key.stop is not None:
                stop = TimeValue(key.stop)
            if key.step is not None:
                if isinstance(key.step, int):
                    skip = key.step
                else:
                    rate = Fraction(TimeOffset.MAX_NANOSEC, TimeValue(key.step).as_timeoffset().to_nanosec())

            rng = TimeValueRange(start, stop, rate=rate)
        elif isinstance(key, TimeValueRange):
            rng = key
        elif isinstance(key, (TimeRange, CountRange)):
            rng = TimeValueRange(key)
        elif isinstance(key, TimeValue):
            val = key
        elif isinstance(key, (Timestamp, TimeOffset, int, SupportsMediaTimeOffset, SupportsMediaTimestamp)):
            val = TimeValue(key)
        elif isinstance(key, SupportsMediaTimeRange):
            rng = TimeValueRange(key)
        else:
            raise ValueError(f"Invalid key: {key!r}")

        if rng is not None and not rng.bounded_before():
            raise ValueError(f"TimeValueRange {rng!r} start must be bounded for the pattern generator")

        if val is not None:
            grain = self.get(val)
            if grain is not None:
                return grain
            else:
                raise KeyError(f"TimeValue {val!r} does not identify a grain in this pattern generator")
        else:
            return self.get_range(rng, skip=skip)

    def get_range(self, rng: TimeValueRange, skip: int = 1) -> Iterator[G]:
        if skip == 1:
            return (grain for grain in (self.get(tv) for tv in rng) if grain is not None)
        else:
            return (grain for grain in (self.get(tv) for (i, tv) in zip(itertools.count(), rng) if i % skip == 0) if grain is not None)

    @abstractmethod
    def get(self, key: TimeValue, default: Optional[G] = None) -> Optional[G]:
        ...

    def __contains__(self, key: TimeValueConstructTypes) -> bool:
        return (self.get(TimeValue(key)) is not None)


class FixedRatePatternGenerator (Generic[G], PatternGenerator[G], metaclass=ABCMeta):
    def __init__(self, rate: Fraction):
        super().__init__()
        self._rate = rate

    @property
    def rate(self) -> Fraction:
        return self._rate

    def get_range(self, rng: TimeValueRange, skip: int = 1) -> Iterator[G]:
        if rng.rate is None:
            rng = TimeValueRange(rng, rate=self._rate)
        return super().get_range(rng, skip=skip)
