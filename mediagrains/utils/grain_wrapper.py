#
# Copyright 2019 British Broadcasting Corporation
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

"""\
Support for reading raw essence data and wrapping it in Grains, or reading Grains and returning essence data.
This can be used for tasks like piping the output of ffmpeg (or similar) into a GSF file.
"""
import typing
import copy

from mediatimestamp.immutable import TimeRange

from ..grain import GRAIN


class GrainWrapper(object):
    """Raw input and wrap it in Grains"""
    def __init__(
        self,
        grain_constructor: typing.Callable,
        input_data: typing.IO[bytes],
        **kwargs
    ):
        """Set up the wrapper and the Grains that will be generated

        :param grain_constructor: One of the Grain constructor functions, used to generate Grains for this media.
        :param input_data: An object to read video data from
        :param **kwargs: Remaining arguments will be passed through to Grain constructor (and Grain defaults will be
                         used for any that are missing)
        """
        self.template_grain = grain_constructor(**kwargs)
        self.input_data = input_data

        # The constructor for a Grain should allocate the right amount of storage for the frame if no data are given,
        # so we take advantage of this calculation to work out how long the frames are
        self.frame_size = len(self.template_grain.data)

    def grains(self) -> typing.Iterator[GRAIN]:
        """Generator that yields Grains read from the input given

        :yields: Grain objects read from the raw input supplied
        """
        grain_timerange = TimeRange.from_start(self.template_grain.origin_timestamp)

        for timestamp in grain_timerange.at_rate(self.template_grain.rate):
            new_grain = copy.deepcopy(self.template_grain)
            new_grain.origin_timestamp = timestamp

            grain_data = self.input_data.read(self.frame_size)

            if grain_data:
                new_grain.data = grain_data
                yield new_grain
            else:
                break
